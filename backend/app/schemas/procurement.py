from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import PaymentMethod, PurchaseOrderStatus


class SupplierCreate(BaseModel):
    code: str
    name: str
    contact_info: str | None = None


class SupplierOut(SupplierCreate):
    id: int
    is_active: bool

    model_config = {"from_attributes": True}


class PurchaseOrderLineIn(BaseModel):
    charge_item_id: int
    quantity: Decimal
    unit_cost: Decimal


class PurchaseOrderLineOut(BaseModel):
    id: int
    charge_item_id: int
    description: str
    quantity: Decimal
    unit_cost: Decimal
    amount: Decimal

    model_config = {"from_attributes": True}


class PurchaseOrderCreate(BaseModel):
    branch_id: int
    supplier_id: int
    currency_code: str
    lines: list[PurchaseOrderLineIn]


class PurchaseOrderOut(BaseModel):
    id: int
    branch_id: int
    supplier_id: int
    po_number: str
    currency_code: str
    status: PurchaseOrderStatus
    subtotal: Decimal
    total: Decimal
    amount_paid: Decimal
    created_at: datetime
    lines: list[PurchaseOrderLineOut] = []

    model_config = {"from_attributes": True}


class SupplierPaymentCreate(BaseModel):
    branch_id: int
    purchase_order_id: int
    method: PaymentMethod
    currency_code: str
    amount: Decimal


class SupplierPaymentOut(SupplierPaymentCreate):
    id: int
    idempotency_key: str

    model_config = {"from_attributes": True}
