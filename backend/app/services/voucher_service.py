import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit_log
from app.models.enums import AuditAction, CashVoucherStatus, PaymentMethod, PurchaseOrderStatus, RoleEnum
from app.models.procurement import PurchaseOrder
from app.models.user import User
from app.models.voucher import CashVoucher
from app.schemas.procurement import SupplierPaymentCreate
from app.schemas.voucher import CashVoucherCreate
from app.services.posting_service import PostingError
from app.services.procurement_service import record_supplier_payment

# A voucher in one of these states has claimed part of the PO's balance.
_OPEN_STATUSES = (CashVoucherStatus.PENDING_CONFIRMATION, CashVoucherStatus.CONFIRMED)


def _generate_number() -> str:
    return f"CV-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"


def _require_role(user: User, role: RoleEnum, action: str) -> None:
    if user.role != role:
        raise PostingError(f"Only the {role.value.replace('_', ' ')} can {action}")


def _require_status(voucher: CashVoucher, expected: CashVoucherStatus, action: str) -> None:
    if voucher.status != expected:
        raise PostingError(f"Voucher {voucher.voucher_number} is {voucher.status.value} — cannot {action}")


async def _amount_already_vouchered(db: AsyncSession, purchase_order_id: int) -> Decimal:
    total = (
        await db.execute(
            select(func.coalesce(func.sum(CashVoucher.amount), 0)).where(
                CashVoucher.purchase_order_id == purchase_order_id, CashVoucher.status.in_(_OPEN_STATUSES)
            )
        )
    ).scalar_one()
    return Decimal(total)


async def create_voucher(db: AsyncSession, voucher_in: CashVoucherCreate, user: User) -> CashVoucher:
    if voucher_in.amount <= 0:
        raise PostingError("Voucher amount must be positive")
    if voucher_in.method == PaymentMethod.MEDICAL_AID:
        raise PostingError("A supplier cannot be paid by medical aid")

    po = await db.get(PurchaseOrder, voucher_in.purchase_order_id)
    if po is None:
        raise PostingError(f"Unknown purchase_order_id {voucher_in.purchase_order_id}")
    if po.branch_id != voucher_in.branch_id:
        raise PostingError("Purchase order belongs to a different branch")
    if po.status not in (PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.PARTIALLY_PAID):
        raise PostingError(f"Purchase order {po.po_number} is {po.status.value} — goods must be received before paying")

    available = po.total - po.amount_paid - await _amount_already_vouchered(db, po.id)
    if voucher_in.amount > available:
        raise PostingError(
            f"Voucher amount {voucher_in.amount} exceeds the {available} still payable on {po.po_number} "
            "(after other open vouchers)"
        )

    voucher = CashVoucher(
        branch_id=po.branch_id,
        voucher_number=_generate_number(),
        purchase_order_id=po.id,
        method=voucher_in.method,
        currency_code=po.currency_code,
        amount=voucher_in.amount,
        description=voucher_in.description,
        status=CashVoucherStatus.PENDING_CONFIRMATION,
        prepared_by_id=user.id,
    )
    db.add(voucher)
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=voucher.branch_id,
        table_name="cash_vouchers",
        record_id=voucher.id,
        action=AuditAction.CREATE,
        after={"voucher_number": voucher.voucher_number, "amount": str(voucher.amount), "po": po.po_number},
    )
    return voucher


async def confirm_voucher(db: AsyncSession, voucher: CashVoucher, user: User) -> CashVoucher:
    """Accountant signature: confirms the payment may proceed."""
    _require_role(user, RoleEnum.ACCOUNTANT, "confirm a cash voucher")
    _require_status(voucher, CashVoucherStatus.PENDING_CONFIRMATION, "confirm")
    if voucher.prepared_by_id == user.id:
        raise PostingError("You prepared this voucher — a different accountant must confirm it")

    voucher.status = CashVoucherStatus.CONFIRMED
    voucher.accountant_id = user.id
    voucher.accountant_name = user.full_name
    voucher.accountant_signed_at = datetime.now(timezone.utc)
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=voucher.branch_id,
        table_name="cash_vouchers",
        record_id=voucher.id,
        action=AuditAction.UPDATE,
        before={"status": CashVoucherStatus.PENDING_CONFIRMATION.value},
        after={"status": voucher.status.value, "signed": "accountant"},
    )
    return voucher


async def reject_voucher(db: AsyncSession, voucher: CashVoucher, user: User, reason: str) -> CashVoucher:
    """Accountant declines to let the payment proceed."""
    _require_role(user, RoleEnum.ACCOUNTANT, "reject a cash voucher")
    _require_status(voucher, CashVoucherStatus.PENDING_CONFIRMATION, "reject")
    if not reason.strip():
        raise PostingError("A reason is required to reject a voucher")

    voucher.status = CashVoucherStatus.REJECTED
    voucher.rejection_reason = reason.strip()
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=voucher.branch_id,
        table_name="cash_vouchers",
        record_id=voucher.id,
        action=AuditAction.UPDATE,
        before={"status": CashVoucherStatus.PENDING_CONFIRMATION.value},
        after={"status": voucher.status.value, "reason": voucher.rejection_reason},
    )
    return voucher


async def cancel_voucher(db: AsyncSession, voucher: CashVoucher, user: User, reason: str) -> CashVoucher:
    if voucher.status not in _OPEN_STATUSES:
        raise PostingError(f"Voucher {voucher.voucher_number} is {voucher.status.value} — cannot cancel")
    if not reason.strip():
        raise PostingError("A reason is required to cancel a voucher")

    before_status = voucher.status
    voucher.status = CashVoucherStatus.CANCELLED
    voucher.rejection_reason = reason.strip()
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=voucher.branch_id,
        table_name="cash_vouchers",
        record_id=voucher.id,
        action=AuditAction.VOID,
        before={"status": before_status.value},
        after={"status": voucher.status.value, "reason": voucher.rejection_reason},
    )
    return voucher


async def disburse_voucher(db: AsyncSession, voucher: CashVoucher, user: User) -> CashVoucher:
    """Accounts Clerk signature: cash goes out, and the supplier payment is
    posted to the ledger in the same transaction."""
    _require_role(user, RoleEnum.ACCOUNTS_CLERK, "disburse cash on a voucher")
    _require_status(voucher, CashVoucherStatus.CONFIRMED, "disburse")

    payment, _created = await record_supplier_payment(
        db,
        SupplierPaymentCreate(
            branch_id=voucher.branch_id,
            purchase_order_id=voucher.purchase_order_id,
            method=voucher.method,
            currency_code=voucher.currency_code,
            amount=voucher.amount,
        ),
        user,
        idempotency_key=f"voucher-{voucher.id}",
    )

    voucher.status = CashVoucherStatus.DISBURSED
    voucher.clerk_id = user.id
    voucher.clerk_name = user.full_name
    voucher.clerk_signed_at = datetime.now(timezone.utc)
    voucher.supplier_payment_id = payment.id
    await db.flush()
    await write_audit_log(
        db,
        actor_id=user.id,
        branch_id=voucher.branch_id,
        table_name="cash_vouchers",
        record_id=voucher.id,
        action=AuditAction.UPDATE,
        before={"status": CashVoucherStatus.CONFIRMED.value},
        after={"status": voucher.status.value, "signed": "accounts_clerk", "supplier_payment_id": payment.id},
    )
    return voucher
