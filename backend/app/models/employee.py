from datetime import date

from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import EmployeeStatus, EmploymentType


class Employee(Base, TimestampMixin):
    """An HR/payroll record. Deliberately separate from User — most staff
    never log into the system, and payroll is run off this table, not User."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    employee_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    national_id: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(200))
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str] = mapped_column(String(100), nullable=False)
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(EmploymentType), nullable=False, default=EmploymentType.FULL_TIME
    )
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[EmployeeStatus] = mapped_column(Enum(EmployeeStatus), nullable=False, default=EmployeeStatus.ACTIVE)
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    bank_name: Mapped[str | None] = mapped_column(String(150))
    bank_account_number: Mapped[str | None] = mapped_column(String(50))
    next_of_kin_name: Mapped[str | None] = mapped_column(String(150))
    next_of_kin_phone: Mapped[str | None] = mapped_column(String(30))
