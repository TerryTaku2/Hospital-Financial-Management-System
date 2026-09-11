import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import require_role, verify_csrf
from app.models.asset import Asset
from app.models.enums import RoleEnum
from app.schemas.asset import AssetCreate, AssetOut, AssetUpdate

router = APIRouter(prefix="/api/assets", tags=["assets"], dependencies=[Depends(verify_csrf)])
CAN_WRITE = require_role(RoleEnum.ADMIN, RoleEnum.ACCOUNTANT)


def _generate_asset_code() -> str:
    return f"AST-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3).upper()}"


async def _get_asset_or_404(db: AsyncSession, asset_id: int) -> Asset:
    asset = await db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")
    return asset


@router.get("", response_model=list[AssetOut])
async def list_assets(
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[Asset]:
    stmt = select(Asset).order_by(Asset.asset_name)
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(Asset.branch_id == effective_branch_id)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{asset_id}", response_model=AssetOut)
async def get_asset(
    asset_id: int, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> Asset:
    asset = await _get_asset_or_404(db, asset_id)
    scope.check_access(asset.branch_id)
    return asset


@router.post("", response_model=AssetOut, dependencies=[Depends(CAN_WRITE)])
async def create_asset(
    asset_in: AssetCreate, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> Asset:
    scope.check_write(asset_in.branch_id)
    asset = Asset(asset_code=_generate_asset_code(), **asset_in.model_dump())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.patch("/{asset_id}", response_model=AssetOut, dependencies=[Depends(CAN_WRITE)])
async def update_asset(
    asset_id: int,
    asset_in: AssetUpdate,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> Asset:
    asset = await _get_asset_or_404(db, asset_id)
    scope.check_write(asset.branch_id)
    for field, value in asset_in.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    await db.commit()
    await db.refresh(asset)
    return asset
