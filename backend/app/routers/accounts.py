from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.accounting import Account, JournalEntry, JournalLine
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.accounting import AccountCreate, AccountOut, JournalLineOut

router = APIRouter(prefix="/api/accounts", tags=["accounts"], dependencies=[Depends(verify_csrf)])


@router.get("", response_model=list[AccountOut])
async def list_accounts(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> list[Account]:
    return list((await db.execute(select(Account).order_by(Account.code))).scalars().all())


@router.post(
    "", response_model=AccountOut, dependencies=[Depends(require_role(RoleEnum.ADMIN, RoleEnum.ACCOUNTANT))]
)
async def create_account(account_in: AccountCreate, db: AsyncSession = Depends(get_db)) -> Account:
    account = Account(**account_in.model_dump())
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/{account_id}/ledger", response_model=list[JournalLineOut])
async def account_ledger(
    account_id: int,
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[JournalLine]:
    account = await db.get(Account, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    stmt = (
        select(JournalLine)
        .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
        .where(JournalLine.account_id == account_id)
        .order_by(JournalLine.id)
    )
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(JournalEntry.branch_id == effective_branch_id)
    return list((await db.execute(stmt)).scalars().all())
