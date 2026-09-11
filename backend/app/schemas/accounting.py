from datetime import date
from decimal import Decimal

from pydantic import BaseModel, model_validator

from app.models.enums import AccountType


class AccountCreate(BaseModel):
    code: str
    name: str
    type: AccountType
    parent_id: int | None = None


class AccountOut(AccountCreate):
    id: int
    is_active: bool

    model_config = {"from_attributes": True}


class AccountUpdate(BaseModel):
    """`code` is deliberately not editable here — a fixed set of codes
    (see app/services/coa_codes.py) are looked up by the posting service
    for every invoice/payment/deposit/claim/purchase-order/payroll action,
    so changing one out from under it would break those flows."""

    name: str | None = None
    type: AccountType | None = None
    parent_id: int | None = None
    is_active: bool | None = None


class JournalLineIn(BaseModel):
    account_id: int
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")

    @model_validator(mode="after")
    def one_side_only(self) -> "JournalLineIn":
        if (self.debit > 0) == (self.credit > 0):
            raise ValueError("Each line must have exactly one of debit or credit greater than zero")
        return self


class JournalEntryCreate(BaseModel):
    branch_id: int
    entry_date: date
    memo: str
    currency_code: str
    lines: list[JournalLineIn]

    @model_validator(mode="after")
    def must_balance(self) -> "JournalEntryCreate":
        if len(self.lines) < 2:
            raise ValueError("A journal entry needs at least two lines")
        total_debit = sum((line.debit for line in self.lines), Decimal("0"))
        total_credit = sum((line.credit for line in self.lines), Decimal("0"))
        if total_debit != total_credit:
            raise ValueError(f"Journal entry does not balance: debit={total_debit} credit={total_credit}")
        return self


class JournalLineOut(BaseModel):
    id: int
    account_id: int
    debit: Decimal
    credit: Decimal
    currency_code: str
    base_amount_debit: Decimal
    base_amount_credit: Decimal

    model_config = {"from_attributes": True}


class JournalEntryOut(BaseModel):
    id: int
    branch_id: int
    entry_date: date
    memo: str
    currency_code: str
    source_type: str
    source_id: int | None
    is_posted: bool
    lines: list[JournalLineOut] = []

    model_config = {"from_attributes": True}
