import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit_log
from app.models.billing import ChargeItem, Invoice, InvoiceLine
from app.models.enums import AuditAction, InvoiceStatus, JournalSourceType, StockLocation
from app.models.patient import Patient
from app.models.user import User
from app.schemas.billing import InvoiceCreate
from app.services import account_lookup, coa_codes, inventory_service
from app.services.posting_service import LineInput, PostingError, post_journal_entry


def _generate_invoice_number() -> str:
    return f"INV-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"


async def _revenue_account_id_for_line(db: AsyncSession, line: InvoiceLine) -> int:
    if line.charge_item_id is None:
        return await account_lookup.get_account_id_by_code(db, coa_codes.REVENUE_GENERAL)
    charge_item = await db.get(ChargeItem, line.charge_item_id)
    return charge_item.revenue_account_id


async def _adjust_pharmacy_stock(db: AsyncSession, invoice: Invoice, sign: int) -> None:
    """Dispensing a pharmacy line draws down the Pharmacy location's stock
    balance; voiding a finalized invoice puts it back. Soft tracking — never
    blocks billing on low/negative stock, it's informational (see
    reorder_level on ChargeItem). Pharmacy stock only exists once Stores has
    issued a requisition into it — see app.services.inventory_service."""
    for line in invoice.lines:
        if line.charge_item_id is None:
            continue
        charge_item = await db.get(ChargeItem, line.charge_item_id)
        if charge_item.category == "Pharmacy":
            await inventory_service.adjust_balance(db, charge_item.id, StockLocation.PHARMACY, sign * line.quantity)


async def create_invoice(db: AsyncSession, invoice_in: InvoiceCreate, user: User) -> Invoice:
    if not invoice_in.lines:
        raise PostingError("An invoice needs at least one line")

    patient_id = invoice_in.patient_id
    if patient_id is None:
        patient = Patient(branch_id=invoice_in.branch_id, **invoice_in.new_patient.model_dump())
        db.add(patient)
        await db.flush()
        await write_audit_log(
            db,
            actor_id=user.id,
            branch_id=patient.branch_id,
            table_name="patients",
            record_id=patient.id,
            action=AuditAction.CREATE,
            after={"first_name": patient.first_name, "last_name": patient.last_name, "auto_registered_at_billing": True},
        )
        patient_id = patient.id

    charge_item_ids = {line.charge_item_id for line in invoice_in.lines if line.charge_item_id is not None}
    charge_items: dict[int, ChargeItem] = {}
    for charge_item_id in charge_item_ids:
        item = await db.get(ChargeItem, charge_item_id)
        if item is None or not item.is_active:
            raise PostingError(f"Unknown or inactive charge item {charge_item_id}")
        if item.branch_id != invoice_in.branch_id:
            raise PostingError(f"Charge item {charge_item_id} belongs to a different branch")
        charge_items[charge_item_id] = item

    invoice = Invoice(
        branch_id=invoice_in.branch_id,
        patient_id=patient_id,
        encounter_id=invoice_in.encounter_id,
        invoice_number=_generate_invoice_number(),
        currency_code=invoice_in.currency_code,
        payer_type=invoice_in.payer_type,
        medical_aid_provider_id=invoice_in.medical_aid_provider_id,
        status=InvoiceStatus.DRAFT,
        created_by_id=user.id,
    )
    db.add(invoice)
    await db.flush()

    subtotal = Decimal("0")
    for line_in in invoice_in.lines:
        item = charge_items[line_in.charge_item_id] if line_in.charge_item_id is not None else None
        unit_price = line_in.unit_price if line_in.unit_price is not None else item.default_price
        amount = (unit_price * line_in.quantity).quantize(Decimal("0.01"))
        subtotal += amount
        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                charge_item_id=item.id if item is not None else None,
                description=line_in.description or item.name,
                quantity=line_in.quantity,
                unit_price=unit_price,
                amount=amount,
            )
        )

    invoice.subtotal = subtotal
    invoice.total = subtotal
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=invoice.branch_id,
        table_name="invoices",
        record_id=invoice.id,
        action=AuditAction.CREATE,
        after={"invoice_number": invoice.invoice_number, "total": str(invoice.total)},
    )
    await db.refresh(invoice, attribute_names=["lines"])
    return invoice


async def finalize_invoice(db: AsyncSession, invoice: Invoice, user: User) -> Invoice:
    if invoice.status != InvoiceStatus.DRAFT:
        raise PostingError(f"Invoice {invoice.id} is {invoice.status.value}, not draft — cannot finalize")

    ar_account_id = await account_lookup.get_ar_account_id(db, invoice)

    revenue_totals: dict[int, Decimal] = {}
    for line in invoice.lines:
        revenue_account_id = await _revenue_account_id_for_line(db, line)
        revenue_totals[revenue_account_id] = revenue_totals.get(revenue_account_id, Decimal("0")) + line.amount

    lines = [LineInput(account_id=ar_account_id, debit=invoice.total)]
    lines += [LineInput(account_id=acct_id, credit=amount) for acct_id, amount in revenue_totals.items()]

    await post_journal_entry(
        db,
        branch_id=invoice.branch_id,
        entry_date=datetime.now(timezone.utc).date(),
        memo=f"Invoice {invoice.invoice_number} finalized",
        currency_code=invoice.currency_code,
        source_type=JournalSourceType.INVOICE,
        source_id=invoice.id,
        created_by_id=user.id,
        lines=lines,
    )
    await _adjust_pharmacy_stock(db, invoice, sign=-1)

    before_status = invoice.status
    invoice.status = InvoiceStatus.FINALIZED
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=invoice.branch_id,
        table_name="invoices",
        record_id=invoice.id,
        action=AuditAction.UPDATE,
        before={"status": before_status.value},
        after={"status": invoice.status.value},
    )
    return invoice


async def void_invoice(db: AsyncSession, invoice: Invoice, user: User, reason: str) -> Invoice:
    if invoice.status not in (InvoiceStatus.DRAFT, InvoiceStatus.FINALIZED):
        raise PostingError(f"Invoice {invoice.id} cannot be voided from status {invoice.status.value}")
    if invoice.amount_paid > 0:
        raise PostingError("Cannot void an invoice that already has payments recorded — refund first")

    before_status = invoice.status
    was_finalized = invoice.status == InvoiceStatus.FINALIZED
    invoice.status = InvoiceStatus.VOID
    await db.flush()

    if was_finalized:
        ar_account_id = await account_lookup.get_ar_account_id(db, invoice)
        revenue_totals: dict[int, Decimal] = {}
        for line in invoice.lines:
            revenue_account_id = await _revenue_account_id_for_line(db, line)
            revenue_totals[revenue_account_id] = revenue_totals.get(revenue_account_id, Decimal("0")) + line.amount
        reversal_lines = [LineInput(account_id=ar_account_id, credit=invoice.total)]
        reversal_lines += [LineInput(account_id=acct_id, debit=amount) for acct_id, amount in revenue_totals.items()]
        await post_journal_entry(
            db,
            branch_id=invoice.branch_id,
            entry_date=datetime.now(timezone.utc).date(),
            memo=f"Invoice {invoice.invoice_number} voided: {reason}",
            currency_code=invoice.currency_code,
            source_type=JournalSourceType.INVOICE,
            source_id=invoice.id,
            created_by_id=user.id,
            lines=reversal_lines,
        )
        await _adjust_pharmacy_stock(db, invoice, sign=1)

    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=invoice.branch_id,
        table_name="invoices",
        record_id=invoice.id,
        action=AuditAction.VOID,
        before={"status": before_status.value},
        after={"status": invoice.status.value, "reason": reason},
    )
    return invoice
