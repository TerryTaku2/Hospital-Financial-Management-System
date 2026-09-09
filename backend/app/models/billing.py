from decimal import Decimal

from sqlalchemy import Boolean, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import DepositStatus, InvoiceStatus, PayerType, PaymentMethod


class ChargeItem(Base, TimestampMixin):
    __tablename__ = "charge_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    default_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    revenue_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reorder_level: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id"))
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    payer_type: Mapped[PayerType] = mapped_column(Enum(PayerType), nullable=False, default=PayerType.PATIENT)
    medical_aid_provider_id: Mapped[int | None] = mapped_column(ForeignKey("medical_aid_providers.id"))
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    lines: Mapped[list["InvoiceLine"]] = relationship(back_populates="invoice", lazy="selectin")


class InvoiceLine(Base, TimestampMixin):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    charge_item_id: Mapped[int | None] = mapped_column(ForeignKey("charge_items.id"))
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("1"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    invoice: Mapped["Invoice"] = relationship(back_populates="lines")


class Deposit(Base, TimestampMixin):
    __tablename__ = "deposits"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id"))
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    amount_applied: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    amount_refunded: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    status: Mapped[DepositStatus] = mapped_column(Enum(DepositStatus), nullable=False, default=DepositStatus.HELD)
    received_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    payer_type: Mapped[PayerType] = mapped_column(Enum(PayerType), nullable=False)
    medical_aid_provider_id: Mapped[int | None] = mapped_column(ForeignKey("medical_aid_providers.id"))
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    received_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)


class Refund(Base, TimestampMixin):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    deposit_id: Mapped[int | None] = mapped_column(ForeignKey("deposits.id"))
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"))
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    processed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
