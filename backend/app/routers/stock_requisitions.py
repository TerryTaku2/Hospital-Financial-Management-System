from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.enums import RoleEnum
from app.models.inventory import StockRequisition
from app.models.user import User
from app.schemas.inventory import StockRequisitionCreate, StockRequisitionOut
from app.services.inventory_service import cancel_requisition, create_requisition, issue_requisition
from app.services.posting_service import PostingError

router = APIRouter(prefix="/api/stock-requisitions", tags=["stock-requisitions"], dependencies=[Depends(verify_csrf)])

CAN_MANAGE_REQUISITIONS = require_role(RoleEnum.ADMIN, RoleEnum.CASHIER, RoleEnum.ACCOUNTANT)


class CancelRequest(BaseModel):
    reason: str


async def _get_requisition_or_404(db: AsyncSession, req_id: int) -> StockRequisition:
    requisition = await db.get(StockRequisition, req_id)
    if requisition is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stock requisition not found")
    return requisition


@router.get("", response_model=list[StockRequisitionOut])
async def list_requisitions(
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[StockRequisition]:
    stmt = select(StockRequisition).order_by(StockRequisition.id.desc())
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(StockRequisition.branch_id == effective_branch_id)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{req_id}", response_model=StockRequisitionOut)
async def get_requisition(
    req_id: int, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> StockRequisition:
    requisition = await _get_requisition_or_404(db, req_id)
    scope.check_access(requisition.branch_id)
    return requisition


@router.post("", response_model=StockRequisitionOut, dependencies=[Depends(CAN_MANAGE_REQUISITIONS)])
async def create_requisition_endpoint(
    req_in: StockRequisitionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> StockRequisition:
    scope.check_write(req_in.branch_id)
    try:
        requisition = await create_requisition(db, req_in, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(requisition, attribute_names=["lines"])
    return requisition


@router.post("/{req_id}/issue", response_model=StockRequisitionOut, dependencies=[Depends(CAN_MANAGE_REQUISITIONS)])
async def issue_requisition_endpoint(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> StockRequisition:
    requisition = await _get_requisition_or_404(db, req_id)
    scope.check_access(requisition.branch_id)
    try:
        requisition = await issue_requisition(db, requisition, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(requisition, attribute_names=["lines"])
    return requisition


@router.post("/{req_id}/cancel", response_model=StockRequisitionOut, dependencies=[Depends(CAN_MANAGE_REQUISITIONS)])
async def cancel_requisition_endpoint(
    req_id: int,
    cancel_in: CancelRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> StockRequisition:
    requisition = await _get_requisition_or_404(db, req_id)
    scope.check_access(requisition.branch_id)
    try:
        requisition = await cancel_requisition(db, requisition, user, cancel_in.reason)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(requisition, attribute_names=["lines"])
    return requisition
