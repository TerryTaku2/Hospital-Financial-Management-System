from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import PaymentMethod, PayrollRunStatus


class PayrollRunCreate(BaseModel):
    branch_id: int
    period_start: date
    period_end: date
    currency_code: str


class PayslipItemOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    department: str
    basic_salary: Decimal
    allowances: Decimal
    deductions: Decimal
    gross_pay: Decimal
    net_pay: Decimal
    notes: str | None = None

    model_config = {"from_attributes": True}


class PayrollRunOut(BaseModel):
    id: int
    branch_id: int
    period_start: date
    period_end: date
    currency_code: str
    status: PayrollRunStatus
    total_gross: Decimal
    total_deductions: Decimal
    total_net: Decimal
    created_at: datetime
    finalized_at: datetime | None = None
    paid_at: datetime | None = None
    items: list[PayslipItemOut] = []

    model_config = {"from_attributes": True}


class PayslipItemUpdate(BaseModel):
    allowances: Decimal = Decimal("0")
    deductions: Decimal = Decimal("0")
    notes: str | None = None


class PayrollPayRequest(BaseModel):
    method: PaymentMethod
