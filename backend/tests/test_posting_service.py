from datetime import date
from decimal import Decimal

import pytest

from app.models.enums import JournalSourceType
from app.services.posting_service import LineInput, PostingError, post_journal_entry


@pytest.mark.asyncio
async def test_balanced_entry_posts(db_session, seeded):
    entry = await post_journal_entry(
        db_session,
        branch_id=seeded["branch"].id,
        entry_date=date.today(),
        memo="Test sale",
        currency_code="USD",
        source_type=JournalSourceType.MANUAL,
        source_id=None,
        created_by_id=seeded["user"].id,
        lines=[
            LineInput(account_id=seeded["ar"].id, debit=Decimal("100.00")),
            LineInput(account_id=seeded["revenue"].id, credit=Decimal("100.00")),
        ],
    )
    assert len(entry.lines) == 2
    assert sum(line.debit for line in entry.lines) == sum(line.credit for line in entry.lines)


@pytest.mark.asyncio
async def test_unbalanced_entry_rejected(db_session, seeded):
    with pytest.raises(PostingError):
        await post_journal_entry(
            db_session,
            branch_id=seeded["branch"].id,
            entry_date=date.today(),
            memo="Bad entry",
            currency_code="USD",
            source_type=JournalSourceType.MANUAL,
            source_id=None,
            created_by_id=seeded["user"].id,
            lines=[
                LineInput(account_id=seeded["ar"].id, debit=Decimal("100.00")),
                LineInput(account_id=seeded["revenue"].id, credit=Decimal("90.00")),
            ],
        )


@pytest.mark.asyncio
async def test_single_line_entry_rejected(db_session, seeded):
    with pytest.raises(PostingError):
        await post_journal_entry(
            db_session,
            branch_id=seeded["branch"].id,
            entry_date=date.today(),
            memo="Single line",
            currency_code="USD",
            source_type=JournalSourceType.MANUAL,
            source_id=None,
            created_by_id=seeded["user"].id,
            lines=[LineInput(account_id=seeded["ar"].id, debit=Decimal("100.00"))],
        )
