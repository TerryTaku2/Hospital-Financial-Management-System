from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import CashVoucherStatus, PaymentMethod


class CashVoucher(Base, TimestampMixin):
    """Authority to pay a supplier. The Accountant signs to confirm the
    payment may proceed; the Accounts Clerk then signs for the disbursement,
    which is the moment the supplier payment is actually posted."""

    __tablename__ = "cash_vouchers"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    voucher_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[CashVoucherStatus] = mapped_column(
        Enum(CashVoucherStatus), nullable=False, default=CashVoucherStatus.PENDING_CONFIRMATION
    )
    prepared_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(300))

    accountant_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    accountant_name: Mapped[str | None] = mapped_column(String(200))
    accountant_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    clerk_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    clerk_name: Mapped[str | None] = mapped_column(String(200))
    clerk_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    supplier_payment_id: Mapped[int | None] = mapped_column(ForeignKey("supplier_payments.id"))
