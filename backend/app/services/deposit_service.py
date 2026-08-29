from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit_log
from app.models.billing import Deposit, Invoice, Refund
from app.models.enums import AuditAction, DepositStatus, InvoiceStatus, JournalSourceType
from app.models.user import User
from app.schemas.billing import DepositApply, DepositCreate, RefundCreate
from app.services import account_lookup, coa_codes
from app.services.posting_service import LineInput, PostingError, post_journal_entry


def _deposit_available(deposit: Deposit) -> Decimal:
    return deposit.amount - deposit.amount_applied - deposit.amount_refunded


async def take_deposit(
    db: AsyncSession, deposit_in: DepositCreate, user: User, idempotency_key: str
) -> tuple[Deposit, bool]:
    existing = (
        await db.execute(select(Deposit).where(Deposit.idempotency_key == idempotency_key))
    ).scalars().first()
    if existing is not None:
        return existing, False

    if deposit_in.amount <= 0:
        raise PostingError("Deposit amount must be positive")

    deposit = Deposit(
        branch_id=deposit_in.branch_id,
        patient_id=deposit_in.patient_id,
        encounter_id=deposit_in.encounter_id,
        currency_code=deposit_in.currency_code,
        amount=deposit_in.amount,
        status=DepositStatus.HELD,
        received_by_id=user.id,
        idempotency_key=idempotency_key,
    )
    db.add(deposit)
    await db.flush()

    cash_account_id = await account_lookup.get_cash_account_id(db, deposit_in.method)
    deposits_held_account_id = await account_lookup.get_account_id_by_code(db, coa_codes.DEPOSITS_HELD)

    await post_journal_entry(
        db,
        branch_id=deposit.branch_id,
        entry_date=datetime.now(timezone.utc).date(),
        memo=f"Deposit received from patient {deposit.patient_id}",
        currency_code=deposit.currency_code,
        source_type=JournalSourceType.DEPOSIT,
        source_id=deposit.id,
        created_by_id=user.id,
        lines=[
            LineInput(account_id=cash_account_id, debit=deposit.amount),
            LineInput(account_id=deposits_held_account_id, credit=deposit.amount),
        ],
    )

    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=deposit.branch_id,
        table_name="deposits",
        record_id=deposit.id,
        action=AuditAction.CREATE,
        after={"amount": str(deposit.amount)},
    )
    return deposit, True


async def apply_deposit(db: AsyncSession, deposit: Deposit, apply_in: DepositApply, user: User) -> Deposit:
    if deposit.status not in (DepositStatus.HELD, DepositStatus.PARTIALLY_APPLIED):
        raise PostingError(f"Deposit {deposit.id} is {deposit.status.value} — nothing left to apply")
    available = _deposit_available(deposit)
    if apply_in.amount <= 0 or apply_in.amount > available:
        raise PostingError(f"Cannot apply {apply_in.amount}; only {available} available on this deposit")

    invoice = await db.get(Invoice, apply_in.invoice_id)
    if invoice is None:
        raise PostingError(f"Unknown invoice_id {apply_in.invoice_id}")
    if invoice.branch_id != deposit.branch_id:
        raise PostingError("A deposit can only be applied to an invoice from the same branch")
    if invoice.status not in (InvoiceStatus.FINALIZED, InvoiceStatus.PARTIALLY_PAID):
        raise PostingError(f"Invoice {invoice.id} is {invoice.status.value} — cannot apply deposit")
    balance = invoice.total - invoice.amount_paid
    if apply_in.amount > balance:
        raise PostingError(f"Deposit application {apply_in.amount} exceeds invoice balance {balance}")

    deposits_held_account_id = await account_lookup.get_account_id_by_code(db, coa_codes.DEPOSITS_HELD)
    ar_account_id = await account_lookup.get_ar_account_id(db, invoice)

    await post_journal_entry(
        db,
        branch_id=deposit.branch_id,
        entry_date=datetime.now(timezone.utc).date(),
        memo=f"Deposit {deposit.id} applied to invoice {invoice.invoice_number}",
        currency_code=deposit.currency_code,
        source_type=JournalSourceType.DEPOSIT_APPLICATION,
        source_id=deposit.id,
        created_by_id=user.id,
        lines=[
            LineInput(account_id=deposits_held_account_id, debit=apply_in.amount),
            LineInput(account_id=ar_account_id, credit=apply_in.amount),
        ],
    )

    deposit.amount_applied += apply_in.amount
    deposit.status = (
        DepositStatus.APPLIED if _deposit_available(deposit) <= 0 else DepositStatus.PARTIALLY_APPLIED
    )
    invoice.amount_paid += apply_in.amount
    invoice.status = InvoiceStatus.PAID if invoice.amount_paid >= invoice.total else InvoiceStatus.PARTIALLY_PAID
    await db.flush()

    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=deposit.branch_id,
        table_name="deposits",
        record_id=deposit.id,
        action=AuditAction.UPDATE,
        after={"applied": str(apply_in.amount), "invoice_id": invoice.id},
    )
    return deposit


async def refund_deposit(
    db: AsyncSession, deposit: Deposit, refund_in: RefundCreate, user: User, idempotency_key: str
) -> tuple[Refund, bool]:
    existing = (
        await db.execute(select(Refund).where(Refund.idempotency_key == idempotency_key))
    ).scalars().first()
    if existing is not None:
        return existing, False

    available = _deposit_available(deposit)
    if refund_in.amount <= 0 or refund_in.amount > available:
        raise PostingError(f"Cannot refund {refund_in.amount}; only {available} available on this deposit")

    refund = Refund(
        branch_id=deposit.branch_id,
        deposit_id=deposit.id,
        invoice_id=None,
        currency_code=deposit.currency_code,
        amount=refund_in.amount,
        reason=refund_in.reason,
        idempotency_key=idempotency_key,
        processed_by_id=user.id,
    )
    db.add(refund)
    await db.flush()

    deposits_held_account_id = await account_lookup.get_account_id_by_code(db, coa_codes.DEPOSITS_HELD)
    cash_account_id = await account_lookup.get_cash_account_id(db, refund_in.method)

    await post_journal_entry(
        db,
        branch_id=deposit.branch_id,
        entry_date=datetime.now(timezone.utc).date(),
        memo=f"Refund of deposit {deposit.id}: {refund_in.reason}",
        currency_code=deposit.currency_code,
        source_type=JournalSourceType.REFUND,
        source_id=refund.id,
        created_by_id=user.id,
        lines=[
            LineInput(account_id=deposits_held_account_id, debit=refund_in.amount),
            LineInput(account_id=cash_account_id, credit=refund_in.amount),
        ],
    )

    deposit.amount_refunded += refund_in.amount
    deposit.status = (
        DepositStatus.REFUNDED if _deposit_available(deposit) <= 0 else DepositStatus.PARTIALLY_APPLIED
    )
    await db.flush()

    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=deposit.branch_id,
        table_name="refunds",
        record_id=refund.id,
        action=AuditAction.CREATE,
        after={"deposit_id": deposit.id, "amount": str(refund.amount)},
    )
    return refund, True
