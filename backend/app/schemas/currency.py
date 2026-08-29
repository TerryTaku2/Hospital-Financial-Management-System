from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CurrencyOut(BaseModel):
    code: str
    name: str
    symbol: str

    model_config = {"from_attributes": True}


class ExchangeRateCreate(BaseModel):
    currency_code: str
    rate_to_base: Decimal
    effective_date: date


class ExchangeRateOut(ExchangeRateCreate):
    id: int

    model_config = {"from_attributes": True}
