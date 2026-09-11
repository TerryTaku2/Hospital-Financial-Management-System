from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import EmployeeStatus, EmploymentType


class EmployeeCreate(BaseModel):
    branch_id: int
    full_name: str
    national_id: str | None = None
    phone: str | None = None
    email: str | None = None
    department: str
    position: str
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    hire_date: date
    basic_salary: Decimal
    currency_code: str
    bank_name: str | None = None
    bank_account_number: str | None = None
    next_of_kin_name: str | None = None
    next_of_kin_phone: str | None = None


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    national_id: str | None = None
    phone: str | None = None
    email: str | None = None
    department: str | None = None
    position: str | None = None
    employment_type: EmploymentType | None = None
    status: EmployeeStatus | None = None
    basic_salary: Decimal | None = None
    bank_name: str | None = None
    bank_account_number: str | None = None
    next_of_kin_name: str | None = None
    next_of_kin_phone: str | None = None


class EmployeeOut(BaseModel):
    id: int
    branch_id: int
    employee_number: str
    full_name: str
    national_id: str | None = None
    phone: str | None = None
    email: str | None = None
    department: str
    position: str
    employment_type: EmploymentType
    hire_date: date
    status: EmployeeStatus
    basic_salary: Decimal
    currency_code: str
    bank_name: str | None = None
    bank_account_number: str | None = None
    next_of_kin_name: str | None = None
    next_of_kin_phone: str | None = None

    model_config = {"from_attributes": True}
