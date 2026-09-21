from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, utcnow
from app.models.enums import RequisitionSignatory, RequisitionStatus


class PurchaseRequisition(Base, TimestampMixin):
    """An internal request to buy goods. It needs the Medical Superintendent,
    Matron and Admin signatures before a purchase order can be raised."""

    __tablename__ = "purchase_requisitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    requisition_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    status: Mapped[RequisitionStatus] = mapped_column(
        Enum(RequisitionStatus), nullable=False, default=RequisitionStatus.PENDING_APPROVAL
    )
    justification: Mapped[str | None] = mapped_column(String(500))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(300))
    purchase_order_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_orders.id"))

    lines: Mapped[list["PurchaseRequisitionLine"]] = relationship(back_populates="requisition", lazy="selectin")
    signatures: Mapped[list["RequisitionSignature"]] = relationship(
        back_populates="requisition", lazy="selectin", order_by="RequisitionSignature.id"
    )


class PurchaseRequisitionLine(Base, TimestampMixin):
    __tablename__ = "purchase_requisition_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    requisition_id: Mapped[int] = mapped_column(ForeignKey("purchase_requisitions.id"), nullable=False)
    charge_item_id: Mapped[int] = mapped_column(ForeignKey("charge_items.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    estimated_unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    requisition: Mapped["PurchaseRequisition"] = relationship(back_populates="lines")


class RequisitionSignature(Base):
    __tablename__ = "requisition_signatures"
    __table_args__ = (UniqueConstraint("requisition_id", "signatory", name="uq_requisition_signatory"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    requisition_id: Mapped[int] = mapped_column(ForeignKey("purchase_requisitions.id"), nullable=False)
    signatory: Mapped[RequisitionSignatory] = mapped_column(Enum(RequisitionSignatory), nullable=False)
    signed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    signed_by_name: Mapped[str] = mapped_column(String(200), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    requisition: Mapped["PurchaseRequisition"] = relationship(back_populates="signatures")
