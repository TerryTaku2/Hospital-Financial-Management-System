from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, model_validator

from app.models.enums import DepositStatus, InvoiceStatus, PayerType, PaymentMethod


class ChargeItemCreate(BaseModel):
    branch_id: int
    code: str
    name: str
    category: str
    default_price: Decimal
    currency_code: str
    revenue_account_id: int
    reorder_level: Decimal | None = None


class ChargeItemOut(ChargeItemCreate):
    id: int
    is_active: bool

    model_config = {"from_attributes": True}


class InvoiceLineIn(BaseModel):
    charge_item_id: int | None = None
    description: str | None = None
    quantity: Decimal = Decimal("1")
    unit_price: Decimal | None = None

    @model_validator(mode="after")
    def manual_line_needs_description_and_price(self) -> "InvoiceLineIn":
        if self.charge_item_id is None and (self.description is None or self.unit_price is None):
            raise ValueError("A line without a charge item needs both a description and a unit price")
        return self


class InvoiceLineOut(BaseModel):
    id: int
    charge_item_id: int | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal

    model_config = {"from_attributes": True}


class InvoiceNewPatient(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date | None = None
    sex: str | None = None
    national_id: str | None = None
    phone: str | None = None
    address: str | None = None


class InvoiceCreate(BaseModel):
    branch_id: int
    patient_id: int | None = None
    new_patient: InvoiceNewPatient | None = None
    encounter_id: int | None = None
    currency_code: str
    payer_type: PayerType = PayerType.PATIENT
    medical_aid_provider_id: int | None = None
    lines: list[InvoiceLineIn]

    @model_validator(mode="after")
    def exactly_one_patient_source(self) -> "InvoiceCreate":
        if (self.patient_id is None) == (self.new_patient is None):
            raise ValueError("Provide either patient_id (existing patient) or new_patient (to register one), not both")
        return self


class InvoiceOut(BaseModel):
    id: int
    branch_id: int
    patient_id: int
    encounter_id: int | None
    invoice_number: str
    currency_code: str
    payer_type: PayerType
    medical_aid_provider_id: int | None
    status: InvoiceStatus
    subtotal: Decimal
    total: Decimal
    amount_paid: Decimal
    created_at: datetime
    lines: list[InvoiceLineOut] = []

    model_config = {"from_attributes": True}


class DepositCreate(BaseModel):
    branch_id: int
    patient_id: int
    encounter_id: int | None = None
    currency_code: str
    amount: Decimal
    method: PaymentMethod = PaymentMethod.CASH


class DepositOut(DepositCreate):
    id: int
    amount_applied: Decimal
    amount_refunded: Decimal
    status: DepositStatus
    idempotency_key: str

    model_config = {"from_attributes": True}


class DepositApply(BaseModel):
    invoice_id: int
    amount: Decimal


class PaymentCreate(BaseModel):
    branch_id: int
    invoice_id: int
    payer_type: PayerType = PayerType.PATIENT
    medical_aid_provider_id: int | None = None
    method: PaymentMethod
    currency_code: str
    amount: Decimal


class PaymentOut(PaymentCreate):
    id: int
    idempotency_key: str

    model_config = {"from_attributes": True}


class RefundCreate(BaseModel):
    branch_id: int
    deposit_id: int | None = None
    invoice_id: int | None = None
    currency_code: str
    amount: Decimal
    reason: str
    method: PaymentMethod = PaymentMethod.CASH


class RefundOut(RefundCreate):
    id: int
    idempotency_key: str

    model_config = {"from_attributes": True}
