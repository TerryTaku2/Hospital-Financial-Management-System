import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit_log
from app.models.billing import ChargeItem
from app.models.enums import AuditAction, JournalSourceType, PurchaseOrderStatus, StockLocation
from app.models.procurement import PurchaseOrder, PurchaseOrderLine, SupplierPayment
from app.models.user import User
from app.schemas.procurement import PurchaseOrderCreate, SupplierPaymentCreate
from app.services import account_lookup, coa_codes, inventory_service
from app.services.posting_service import LineInput, PostingError, post_journal_entry


def _generate_po_number() -> str:
    return f"PO-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"


async def create_purchase_order(db: AsyncSession, po_in: PurchaseOrderCreate, user: User) -> PurchaseOrder:
    if not po_in.lines:
        raise PostingError("A purchase order needs at least one line")

    charge_item_ids = {line.charge_item_id for line in po_in.lines}
    charge_items: dict[int, ChargeItem] = {}
    for charge_item_id in charge_item_ids:
        item = await db.get(ChargeItem, charge_item_id)
        if item is None or not item.is_active:
            raise PostingError(f"Unknown or inactive charge item {charge_item_id}")
        if item.branch_id != po_in.branch_id:
            raise PostingError(f"Charge item {charge_item_id} belongs to a different branch")
        charge_items[charge_item_id] = item

    po = PurchaseOrder(
        branch_id=po_in.branch_id,
        supplier_id=po_in.supplier_id,
        po_number=_generate_po_number(),
        currency_code=po_in.currency_code,
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=user.id,
    )
    db.add(po)
    await db.flush()

    subtotal = Decimal("0")
    for line_in in po_in.lines:
        if line_in.quantity <= 0:
            raise PostingError("Purchase order line quantity must be positive")
        item = charge_items[line_in.charge_item_id]
        amount = (line_in.unit_cost * line_in.quantity).quantize(Decimal("0.01"))
        subtotal += amount
        db.add(
            PurchaseOrderLine(
                purchase_order_id=po.id,
                charge_item_id=item.id,
                description=item.name,
                quantity=line_in.quantity,
                unit_cost=line_in.unit_cost,
                amount=amount,
            )
        )

    po.subtotal = subtotal
    po.total = subtotal
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=po.branch_id,
        table_name="purchase_orders",
        record_id=po.id,
        action=AuditAction.CREATE,
        after={"po_number": po.po_number, "total": str(po.total)},
    )
    await db.refresh(po, attribute_names=["lines"])
    return po


async def receive_purchase_order(db: AsyncSession, po: PurchaseOrder, user: User) -> PurchaseOrder:
    if po.status != PurchaseOrderStatus.DRAFT:
        raise PostingError(f"Purchase order {po.id} is {po.status.value}, not draft — cannot receive")

    cogs_account_id = await account_lookup.get_account_id_by_code(db, coa_codes.COGS_DRUGS)
    ap_account_id = await account_lookup.get_account_id_by_code(db, coa_codes.AP_SUPPLIERS)

    for line in po.lines:
        await inventory_service.adjust_balance(db, line.charge_item_id, StockLocation.STORE, line.quantity)

    await post_journal_entry(
        db,
        branch_id=po.branch_id,
        entry_date=datetime.now(timezone.utc).date(),
        memo=f"Purchase order {po.po_number} received",
        currency_code=po.currency_code,
        source_type=JournalSourceType.PURCHASE_ORDER,
        source_id=po.id,
        created_by_id=user.id,
        lines=[
            LineInput(account_id=cogs_account_id, debit=po.total),
            LineInput(account_id=ap_account_id, credit=po.total),
        ],
    )

    before_status = po.status
    po.status = PurchaseOrderStatus.RECEIVED
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=po.branch_id,
        table_name="purchase_orders",
        record_id=po.id,
        action=AuditAction.UPDATE,
        before={"status": before_status.value},
        after={"status": po.status.value},
    )
    return po


async def cancel_purchase_order(db: AsyncSession, po: PurchaseOrder, user: User, reason: str) -> PurchaseOrder:
    if po.status != PurchaseOrderStatus.DRAFT:
        raise PostingError(f"Purchase order {po.id} is {po.status.value} — only a draft order can be cancelled")

    before_status = po.status
    po.status = PurchaseOrderStatus.CANCELLED
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=po.branch_id,
        table_name="purchase_orders",
        record_id=po.id,
        action=AuditAction.VOID,
        before={"status": before_status.value},
        after={"status": po.status.value, "reason": reason},
    )
    return po


async def record_supplier_payment(
    db: AsyncSession, payment_in: SupplierPaymentCreate, user: User, idempotency_key: str
) -> tuple[SupplierPayment, bool]:
    existing = (
        await db.execute(select(SupplierPayment).where(SupplierPayment.idempotency_key == idempotency_key))
    ).scalars().first()
    if existing is not None:
        return existing, False

    if payment_in.amount <= 0:
        raise PostingError("Payment amount must be positive")

    po = await db.get(PurchaseOrder, payment_in.purchase_order_id)
    if po is None:
        raise PostingError(f"Unknown purchase_order_id {payment_in.purchase_order_id}")
    if po.status not in (PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.PARTIALLY_PAID):
        raise PostingError(f"Purchase order {po.id} is {po.status.value} — cannot accept a payment")

    balance = po.total - po.amount_paid
    if payment_in.amount > balance:
        raise PostingError(f"Payment {payment_in.amount} exceeds outstanding balance {balance}")

    payment = SupplierPayment(
        branch_id=payment_in.branch_id,
        purchase_order_id=po.id,
        method=payment_in.method,
        currency_code=payment_in.currency_code,
        amount=payment_in.amount,
        idempotency_key=idempotency_key,
        paid_by_id=user.id,
    )
    db.add(payment)
    await db.flush()

    cash_account_id = await account_lookup.get_cash_account_id(db, payment_in.method)
    ap_account_id = await account_lookup.get_account_id_by_code(db, coa_codes.AP_SUPPLIERS)

    await post_journal_entry(
        db,
        branch_id=po.branch_id,
        entry_date=datetime.now(timezone.utc).date(),
        memo=f"Payment to supplier for purchase order {po.po_number}",
        currency_code=payment_in.currency_code,
        source_type=JournalSourceType.SUPPLIER_PAYMENT,
        source_id=payment.id,
        created_by_id=user.id,
        lines=[
            LineInput(account_id=ap_account_id, debit=payment_in.amount),
            LineInput(account_id=cash_account_id, credit=payment_in.amount),
        ],
    )

    po.amount_paid += payment_in.amount
    po.status = PurchaseOrderStatus.PAID if po.amount_paid >= po.total else PurchaseOrderStatus.PARTIALLY_PAID
    await db.flush()

    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=po.branch_id,
        table_name="supplier_payments",
        record_id=payment.id,
        action=AuditAction.CREATE,
        after={"purchase_order_id": po.id, "amount": str(payment.amount), "method": payment.method.value},
    )
    return payment, True
