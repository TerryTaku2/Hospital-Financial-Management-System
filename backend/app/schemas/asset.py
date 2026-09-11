from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import AssetStatus


class AssetCreate(BaseModel):
    branch_id: int
    asset_name: str
    department: str
    acquisition_date: date
    cost: Decimal
    currency_code: str
    netbook_value: Decimal


class AssetUpdate(BaseModel):
    asset_name: str | None = None
    department: str | None = None
    acquisition_date: date | None = None
    cost: Decimal | None = None
    netbook_value: Decimal | None = None
    status: AssetStatus | None = None


class AssetOut(BaseModel):
    id: int
    branch_id: int
    asset_code: str
    asset_name: str
    department: str
    acquisition_date: date
    cost: Decimal
    currency_code: str
    netbook_value: Decimal
    status: AssetStatus

    model_config = {"from_attributes": True}
