from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.billing import ChargeItem
from app.models.enums import RoleEnum, StockLocation
from app.models.inventory import StockAdjustment, StockBalance
from app.models.user import User
from app.schemas.inventory import StockAdjustmentCreate, StockAdjustmentOut, StockBalanceOut
from app.services import inventory_service
from app.services.posting_service import PostingError

router = APIRouter(prefix="/api/stock", tags=["stock"], dependencies=[Depends(verify_csrf)])

CAN_MANAGE_STOCK = require_role(RoleEnum.ADMIN, RoleEnum.CASHIER, RoleEnum.ACCOUNTANT)


@router.get("/balances", response_model=list[StockBalanceOut])
async def list_balances(
    location: StockLocation | None = None,
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[StockBalance]:
    stmt = select(StockBalance).join(ChargeItem, StockBalance.charge_item_id == ChargeItem.id)
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(ChargeItem.branch_id == effective_branch_id)
    if location is not None:
        stmt = stmt.where(StockBalance.location == location)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/adjustments", response_model=list[StockAdjustmentOut])
async def list_adjustments(
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[StockAdjustment]:
    stmt = select(StockAdjustment).order_by(StockAdjustment.id.desc())
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(StockAdjustment.branch_id == effective_branch_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/adjustments", response_model=StockAdjustmentOut, dependencies=[Depends(CAN_MANAGE_STOCK)])
async def create_adjustment_endpoint(
    adj_in: StockAdjustmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> StockAdjustment:
    scope.check_write(adj_in.branch_id)
    try:
        adjustment = await inventory_service.create_adjustment(db, adj_in, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(adjustment)
    return adjustment
