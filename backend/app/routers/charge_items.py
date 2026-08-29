from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import require_role, verify_csrf
from app.models.billing import ChargeItem
from app.models.enums import RoleEnum
from app.schemas.billing import ChargeItemCreate, ChargeItemOut

router = APIRouter(prefix="/api/charge-items", tags=["charge-items"], dependencies=[Depends(verify_csrf)])


@router.get("", response_model=list[ChargeItemOut])
async def list_charge_items(
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[ChargeItem]:
    stmt = select(ChargeItem).where(ChargeItem.is_active.is_(True))
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(ChargeItem.branch_id == effective_branch_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post(
    "", response_model=ChargeItemOut, dependencies=[Depends(require_role(RoleEnum.ADMIN, RoleEnum.ACCOUNTANT))]
)
async def create_charge_item(
    item_in: ChargeItemCreate, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> ChargeItem:
    scope.check_write(item_in.branch_id)
    item = ChargeItem(**item_in.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item
