from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import JournalEntry, JournalLine
from app.models.branch import Branch
from app.models.currency import ExchangeRate
from app.models.enums import JournalSourceType


class PostingError(ValueError):
    pass


@dataclass
class LineInput:
    account_id: int
    debit: Decimal = field(default=Decimal("0"))
    credit: Decimal = field(default=Decimal("0"))


async def get_rate_to_base(db: AsyncSession, currency_code: str, base_currency_code: str, as_of: date) -> Decimal:
    if currency_code == base_currency_code:
        return Decimal("1")
    stmt = (
        select(ExchangeRate)
        .where(ExchangeRate.currency_code == currency_code, ExchangeRate.effective_date <= as_of)
        .order_by(ExchangeRate.effective_date.desc())
        .limit(1)
    )
    rate = (await db.execute(stmt)).scalars().first()
    if rate is None:
        raise PostingError(f"No exchange rate on file for {currency_code} as of {as_of}")
    return rate.rate_to_base


async def post_journal_entry(
    db: AsyncSession,
    *,
    branch_id: int,
    entry_date: date,
    memo: str,
    currency_code: str,
    source_type: JournalSourceType,
    source_id: int | None,
    created_by_id: int,
    lines: list[LineInput],
) -> JournalEntry:
    """The single place ledger rows get written. Validates the entry balances
    before touching the database so the trial balance can never drift."""
    if len(lines) < 2:
        raise PostingError("A journal entry needs at least two lines")

    for line in lines:
        if (line.debit > 0) == (line.credit > 0):
            raise PostingError("Each journal line must have exactly one of debit or credit greater than zero")

    total_debit = sum((line.debit for line in lines), Decimal("0"))
    total_credit = sum((line.credit for line in lines), Decimal("0"))
    if total_debit != total_credit:
        raise PostingError(f"Journal entry does not balance: debit={total_debit} credit={total_credit}")
    if total_debit <= 0:
        raise PostingError("Journal entry must have a nonzero amount")

    branch = await db.get(Branch, branch_id)
    if branch is None:
        raise PostingError(f"Unknown branch_id {branch_id}")

    rate = await get_rate_to_base(db, currency_code, branch.base_currency_code, entry_date)

    entry = JournalEntry(
        branch_id=branch_id,
        entry_date=entry_date,
        memo=memo,
        currency_code=currency_code,
        source_type=source_type,
        source_id=source_id,
        created_by_id=created_by_id,
    )
    db.add(entry)
    await db.flush()

    for line in lines:
        db.add(
            JournalLine(
                journal_entry_id=entry.id,
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
                currency_code=currency_code,
                base_amount_debit=(line.debit * rate).quantize(Decimal("0.01")),
                base_amount_credit=(line.credit * rate).quantize(Decimal("0.01")),
            )
        )
    await db.flush()
    await db.refresh(entry, attribute_names=["lines"])
    return entry
