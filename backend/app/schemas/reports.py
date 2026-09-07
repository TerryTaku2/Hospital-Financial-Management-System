from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class TrialBalanceLine(BaseModel):
    account_id: int
    account_code: str
    account_name: str
    total_debit: Decimal
    total_credit: Decimal


class TrialBalanceOut(BaseModel):
    lines: list[TrialBalanceLine]
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool


class ArAgingRow(BaseModel):
    debtor_type: str
    debtor_id: int
    debtor_name: str
    bucket_0_30: Decimal
    bucket_31_60: Decimal
    bucket_61_90: Decimal
    bucket_90_plus: Decimal
    total_outstanding: Decimal


class ArAgingOut(BaseModel):
    rows: list[ArAgingRow]
    grand_total: Decimal


class IncomeStatementLine(BaseModel):
    account_id: int
    account_code: str
    account_name: str
    amount: Decimal


class IncomeStatementOut(BaseModel):
    income_lines: list[IncomeStatementLine]
    expense_lines: list[IncomeStatementLine]
    total_income: Decimal
    total_expense: Decimal
    net_income: Decimal


class DailyTransactionRow(BaseModel):
    kind: str
    id: int
    time: datetime
    patient_id: int | None
    patient_name: str | None
    reference: str
    description: str
    method: str | None
    currency_code: str
    amount: Decimal
    status: str


class DailyTransactionsSummary(BaseModel):
    total_invoiced: dict[str, Decimal]
    total_payments: dict[str, Decimal]
    total_deposits: dict[str, Decimal]
    total_refunds: dict[str, Decimal]
    net_cash_collected: dict[str, Decimal]


class DailyTransactionsOut(BaseModel):
    transaction_date: date
    rows: list[DailyTransactionRow]
    summary: DailyTransactionsSummary


class RevenueTrendPoint(BaseModel):
    period: date
    revenue: Decimal


class RevenueTrendOut(BaseModel):
    points: list[RevenueTrendPoint]
