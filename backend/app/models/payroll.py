from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import PayrollRunStatus


class PayrollRun(Base, TimestampMixin):
    """One payroll period for a branch. Draft runs generate one PayslipItem
    per active employee off their basic_salary and can still be edited;
    finalizing posts the accrual to the general ledger and locks the items;
    paying posts the disbursement and is the terminal state alongside void
    (which is only ever reachable from draft, before any GL impact)."""

    __tablename__ = "payroll_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    status: Mapped[PayrollRunStatus] = mapped_column(Enum(PayrollRunStatus), nullable=False, default=PayrollRunStatus.DRAFT)
    total_gross: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    total_net: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["PayslipItem"]] = relationship(back_populates="payroll_run", lazy="selectin")


class PayslipItem(Base, TimestampMixin):
    """employee_name/department are snapshotted at generation time so a
    payslip stays accurate even if the Employee record is edited later."""

    __tablename__ = "payslip_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    payroll_run_id: Mapped[int] = mapped_column(ForeignKey("payroll_runs.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    employee_name: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    allowances: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    deductions: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    payroll_run: Mapped["PayrollRun"] = relationship(back_populates="items")
