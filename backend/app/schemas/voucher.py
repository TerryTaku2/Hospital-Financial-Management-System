from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import CashVoucherStatus, PaymentMethod


class CashVoucherCreate(BaseModel):
    branch_id: int
    purchase_order_id: int
    method: PaymentMethod
    amount: Decimal
    description: str | None = None


class CashVoucherOut(BaseModel):
    id: int
    branch_id: int
    voucher_number: str
    purchase_order_id: int
    method: PaymentMethod
    currency_code: str
    amount: Decimal
    description: str | None
    status: CashVoucherStatus
    prepared_by_id: int
    rejection_reason: str | None
    accountant_name: str | None
    accountant_signed_at: datetime | None
    clerk_name: str | None
    clerk_signed_at: datetime | None
    supplier_payment_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VoucherReason(BaseModel):
    reason: str
