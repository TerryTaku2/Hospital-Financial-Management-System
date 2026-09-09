from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import StockLocation, StockRequisitionStatus


class StockBalance(Base, TimestampMixin):
    """Quantity on hand of a charge item at one physical location. Stores
    receives from suppliers into STORE; Pharmacy requisitions stock from
    STORE into PHARMACY before it can be dispensed to patients."""

    __tablename__ = "stock_balances"
    __table_args__ = (UniqueConstraint("charge_item_id", "location", name="uq_stock_balance_item_location"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    charge_item_id: Mapped[int] = mapped_column(ForeignKey("charge_items.id"), nullable=False)
    location: Mapped[StockLocation] = mapped_column(Enum(StockLocation), nullable=False)
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))


class StockRequisition(Base, TimestampMixin):
    """Pharmacy's internal request to draw stock out of Stores."""

    __tablename__ = "stock_requisitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    requisition_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[StockRequisitionStatus] = mapped_column(
        Enum(StockRequisitionStatus), nullable=False, default=StockRequisitionStatus.DRAFT
    )
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    issued_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    lines: Mapped[list["StockRequisitionLine"]] = relationship(back_populates="requisition", lazy="selectin")


class StockRequisitionLine(Base, TimestampMixin):
    __tablename__ = "stock_requisition_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    requisition_id: Mapped[int] = mapped_column(ForeignKey("stock_requisitions.id"), nullable=False)
    charge_item_id: Mapped[int] = mapped_column(ForeignKey("charge_items.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    requisition: Mapped["StockRequisition"] = relationship(back_populates="lines")


class StockAdjustment(Base, TimestampMixin):
    """A manual correction to a stock balance (wastage, damage, stock count
    correction, etc). Memo-only — there is no inventory asset account in the
    chart of accounts, since purchase order receipts already expense
    straight to COGS, so adjustments carry no journal entry."""

    __tablename__ = "stock_adjustments"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    charge_item_id: Mapped[int] = mapped_column(ForeignKey("charge_items.id"), nullable=False)
    location: Mapped[StockLocation] = mapped_column(Enum(StockLocation), nullable=False)
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    adjusted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
