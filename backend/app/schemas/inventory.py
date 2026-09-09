from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import StockLocation, StockRequisitionStatus


class StockBalanceOut(BaseModel):
    charge_item_id: int
    location: StockLocation
    quantity_on_hand: Decimal

    model_config = {"from_attributes": True}


class StockRequisitionLineIn(BaseModel):
    charge_item_id: int
    quantity: Decimal


class StockRequisitionLineOut(BaseModel):
    id: int
    charge_item_id: int
    description: str
    quantity: Decimal

    model_config = {"from_attributes": True}


class StockRequisitionCreate(BaseModel):
    branch_id: int
    lines: list[StockRequisitionLineIn]


class StockRequisitionOut(BaseModel):
    id: int
    branch_id: int
    requisition_number: str
    status: StockRequisitionStatus
    requested_by_id: int
    issued_by_id: int | None
    created_at: datetime
    lines: list[StockRequisitionLineOut] = []

    model_config = {"from_attributes": True}


class StockAdjustmentCreate(BaseModel):
    branch_id: int
    charge_item_id: int
    location: StockLocation
    quantity_delta: Decimal
    reason: str


class StockAdjustmentOut(StockAdjustmentCreate):
    id: int
    adjusted_by_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
