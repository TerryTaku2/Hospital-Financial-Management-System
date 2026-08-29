from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.accounting import JournalEntry
from app.models.enums import JournalSourceType, RoleEnum
from app.models.user import User
from app.schemas.accounting import JournalEntryCreate, JournalEntryOut
from app.services.posting_service import LineInput, PostingError, post_journal_entry

router = APIRouter(prefix="/api/journal-entries", tags=["journal"], dependencies=[Depends(verify_csrf)])

CAN_POST_JOURNAL = require_role(RoleEnum.ADMIN, RoleEnum.ACCOUNTANT)


@router.get("", response_model=list[JournalEntryOut])
async def list_journal_entries(
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[JournalEntry]:
    stmt = select(JournalEntry).order_by(JournalEntry.id.desc())
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(JournalEntry.branch_id == effective_branch_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=JournalEntryOut, dependencies=[Depends(CAN_POST_JOURNAL)])
async def create_journal_entry(
    entry_in: JournalEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> JournalEntry:
    scope.check_write(entry_in.branch_id)
    try:
        entry = await post_journal_entry(
            db,
            branch_id=entry_in.branch_id,
            entry_date=entry_in.entry_date,
            memo=entry_in.memo,
            currency_code=entry_in.currency_code,
            source_type=JournalSourceType.MANUAL,
            source_id=None,
            created_by_id=user.id,
            lines=[LineInput(account_id=line.account_id, debit=line.debit, credit=line.credit) for line in entry_in.lines],
        )
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(entry, attribute_names=["lines"])
    return entry
