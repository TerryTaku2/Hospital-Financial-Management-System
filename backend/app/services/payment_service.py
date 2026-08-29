from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit_log
from app.models.billing import Invoice, Payment
from app.models.enums import AuditAction, InvoiceStatus, JournalSourceType
from app.models.user import User
from app.schemas.billing import PaymentCreate
from app.services import account_lookup
from app.services.posting_service import LineInput, PostingError, post_journal_entry


async def record_payment(
    db: AsyncSession, payment_in: PaymentCreate, user: User, idempotency_key: str
) -> tuple[Payment, bool]:
    """Returns (payment, created). created=False means this idempotency key
    was already processed and the earlier result is being replayed."""
    existing = (
        await db.execute(select(Payment).where(Payment.idempotency_key == idempotency_key))
    ).scalars().first()
    if existing is not None:
        return existing, False

    if payment_in.amount <= 0:
        raise PostingError("Payment amount must be positive")

    invoice = await db.get(Invoice, payment_in.invoice_id)
    if invoice is None:
        raise PostingError(f"Unknown invoice_id {payment_in.invoice_id}")
    if invoice.status not in (InvoiceStatus.FINALIZED, InvoiceStatus.PARTIALLY_PAID):
        raise PostingError(f"Invoice {invoice.id} is {invoice.status.value} — cannot accept payment")

    balance = invoice.total - invoice.amount_paid
    if payment_in.amount > balance:
        raise PostingError(f"Payment {payment_in.amount} exceeds outstanding balance {balance}")

    payment = Payment(
        branch_id=payment_in.branch_id,
        invoice_id=invoice.id,
        payer_type=payment_in.payer_type,
        medical_aid_provider_id=payment_in.medical_aid_provider_id,
        method=payment_in.method,
        currency_code=payment_in.currency_code,
        amount=payment_in.amount,
        idempotency_key=idempotency_key,
        received_by_id=user.id,
    )
    db.add(payment)
    await db.flush()

    cash_account_id = await account_lookup.get_cash_account_id(db, payment_in.method)
    ar_account_id = await account_lookup.get_ar_account_id(db, invoice)

    await post_journal_entry(
        db,
        branch_id=invoice.branch_id,
        entry_date=datetime.now(timezone.utc).date(),
        memo=f"Payment received for invoice {invoice.invoice_number}",
        currency_code=payment_in.currency_code,
        source_type=JournalSourceType.PAYMENT,
        source_id=payment.id,
        created_by_id=user.id,
        lines=[
            LineInput(account_id=cash_account_id, debit=payment_in.amount),
            LineInput(account_id=ar_account_id, credit=payment_in.amount),
        ],
    )

    invoice.amount_paid += payment_in.amount
    invoice.status = InvoiceStatus.PAID if invoice.amount_paid >= invoice.total else InvoiceStatus.PARTIALLY_PAID
    await db.flush()

    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=invoice.branch_id,
        table_name="payments",
        record_id=payment.id,
        action=AuditAction.CREATE,
        after={"invoice_id": invoice.id, "amount": str(payment.amount), "method": payment.method.value},
    )
    return payment, True
