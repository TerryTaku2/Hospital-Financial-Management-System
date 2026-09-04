from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.schemas.reports import ArAgingOut, DailyTransactionsOut, IncomeStatementOut, TrialBalanceOut
from app.services import reporting_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/trial-balance", response_model=TrialBalanceOut)
async def trial_balance(
    branch_id: int | None = None, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> TrialBalanceOut:
    return await reporting_service.trial_balance(db, scope.resolve_list_filter(branch_id))


@router.get("/income-statement", response_model=IncomeStatementOut)
async def income_statement(
    branch_id: int | None = None, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> IncomeStatementOut:
    return await reporting_service.income_statement(db, scope.resolve_list_filter(branch_id))


@router.get("/ar-aging", response_model=ArAgingOut)
async def ar_aging(
    branch_id: int | None = None, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> ArAgingOut:
    return await reporting_service.ar_aging(db, scope.resolve_list_filter(branch_id))


@router.get("/daily-transactions", response_model=DailyTransactionsOut)
async def daily_transactions(
    transaction_date: date | None = None,
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> DailyTransactionsOut:
    target_date = transaction_date or datetime.now(timezone.utc).date()
    return await reporting_service.daily_transactions(db, target_date, scope.resolve_list_filter(branch_id))
