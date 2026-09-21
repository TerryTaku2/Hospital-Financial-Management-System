from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import RequisitionSignatory, RequisitionStatus


class RequisitionLineIn(BaseModel):
    charge_item_id: int
    quantity: Decimal
    estimated_unit_cost: Decimal


class RequisitionLineOut(BaseModel):
    id: int
    charge_item_id: int
    description: str
    quantity: Decimal
    estimated_unit_cost: Decimal
    amount: Decimal

    model_config = {"from_attributes": True}


class RequisitionCreate(BaseModel):
    branch_id: int
    department: str
    supplier_id: int | None = None
    currency_code: str
    justification: str | None = None
    lines: list[RequisitionLineIn]


class RequisitionSignatureOut(BaseModel):
    signatory: RequisitionSignatory
    signed_by_id: int
    signed_by_name: str
    signed_at: datetime

    model_config = {"from_attributes": True}


class RequisitionOut(BaseModel):
    id: int
    branch_id: int
    requisition_number: str
    department: str
    supplier_id: int | None
    currency_code: str
    status: RequisitionStatus
    justification: str | None
    total: Decimal
    requested_by_id: int
    rejection_reason: str | None
    purchase_order_id: int | None
    created_at: datetime
    lines: list[RequisitionLineOut] = []
    signatures: list[RequisitionSignatureOut] = []

    model_config = {"from_attributes": True}


class RequisitionReason(BaseModel):
    reason: str


class RequisitionToPurchaseOrder(BaseModel):
    """Only needed when the requisition didn't name a supplier."""

    supplier_id: int | None = None
