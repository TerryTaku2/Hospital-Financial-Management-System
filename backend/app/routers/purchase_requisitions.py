from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.enums import RequisitionStatus, RoleEnum
from app.models.procurement import PurchaseOrder
from app.models.requisition import PurchaseRequisition
from app.models.user import User
from app.schemas.procurement import PurchaseOrderOut
from app.schemas.requisition import (
    RequisitionCreate,
    RequisitionOut,
    RequisitionReason,
    RequisitionToPurchaseOrder,
)
from app.services.posting_service import PostingError
from app.services.requisition_service import (
    cancel_requisition,
    create_requisition,
    raise_purchase_order,
    reject_requisition,
    sign_requisition,
)

router = APIRouter(
    prefix="/api/purchase-requisitions", tags=["purchase-requisitions"], dependencies=[Depends(verify_csrf)]
)

CAN_RAISE_REQUISITION = require_role(
    RoleEnum.ADMIN, RoleEnum.MEDICAL_SUPERINTENDENT, RoleEnum.MATRON, RoleEnum.ACCOUNTANT, RoleEnum.CASHIER
)
CAN_SIGN_REQUISITION = require_role(RoleEnum.ADMIN, RoleEnum.MEDICAL_SUPERINTENDENT, RoleEnum.MATRON)
CAN_RAISE_PO = require_role(RoleEnum.ADMIN, RoleEnum.CASHIER, RoleEnum.ACCOUNTANT)


async def _get_or_404(db: AsyncSession, requisition_id: int) -> PurchaseRequisition:
    requisition = await db.get(PurchaseRequisition, requisition_id)
    if requisition is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase requisition not found")
    return requisition


@router.get("", response_model=list[RequisitionOut])
async def list_requisitions(
    status_filter: RequisitionStatus | None = None,
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[PurchaseRequisition]:
    stmt = select(PurchaseRequisition).order_by(PurchaseRequisition.id.desc())
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(PurchaseRequisition.branch_id == effective_branch_id)
    if status_filter is not None:
        stmt = stmt.where(PurchaseRequisition.status == status_filter)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{requisition_id}", response_model=RequisitionOut)
async def get_requisition(
    requisition_id: int, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> PurchaseRequisition:
    requisition = await _get_or_404(db, requisition_id)
    scope.check_access(requisition.branch_id)
    return requisition


@router.post("", response_model=RequisitionOut, dependencies=[Depends(CAN_RAISE_REQUISITION)])
async def create_requisition_endpoint(
    req_in: RequisitionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> PurchaseRequisition:
    scope.check_write(req_in.branch_id)
    try:
        requisition = await create_requisition(db, req_in, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(requisition, attribute_names=["lines", "signatures"])
    return requisition


@router.post("/{requisition_id}/sign", response_model=RequisitionOut, dependencies=[Depends(CAN_SIGN_REQUISITION)])
async def sign_requisition_endpoint(
    requisition_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> PurchaseRequisition:
    requisition = await _get_or_404(db, requisition_id)
    scope.check_access(requisition.branch_id)
    scope.check_write(requisition.branch_id)
    try:
        requisition = await sign_requisition(db, requisition, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(requisition, attribute_names=["lines", "signatures"])
    return requisition


@router.post("/{requisition_id}/reject", response_model=RequisitionOut, dependencies=[Depends(CAN_SIGN_REQUISITION)])
async def reject_requisition_endpoint(
    requisition_id: int,
    body: RequisitionReason,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> PurchaseRequisition:
    requisition = await _get_or_404(db, requisition_id)
    scope.check_access(requisition.branch_id)
    scope.check_write(requisition.branch_id)
    try:
        requisition = await reject_requisition(db, requisition, user, body.reason)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(requisition, attribute_names=["lines", "signatures"])
    return requisition


@router.post("/{requisition_id}/cancel", response_model=RequisitionOut, dependencies=[Depends(CAN_RAISE_REQUISITION)])
async def cancel_requisition_endpoint(
    requisition_id: int,
    body: RequisitionReason,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> PurchaseRequisition:
    requisition = await _get_or_404(db, requisition_id)
    scope.check_access(requisition.branch_id)
    scope.check_write(requisition.branch_id)
    if requisition.requested_by_id != user.id and user.role != RoleEnum.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the requester or an admin can cancel a requisition")
    try:
        requisition = await cancel_requisition(db, requisition, user, body.reason)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(requisition, attribute_names=["lines", "signatures"])
    return requisition


@router.post("/{requisition_id}/purchase-order", response_model=PurchaseOrderOut, dependencies=[Depends(CAN_RAISE_PO)])
async def raise_purchase_order_endpoint(
    requisition_id: int,
    body: RequisitionToPurchaseOrder,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> PurchaseOrder:
    requisition = await _get_or_404(db, requisition_id)
    scope.check_access(requisition.branch_id)
    scope.check_write(requisition.branch_id)
    try:
        po = await raise_purchase_order(db, requisition, user, body.supplier_id)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(po, attribute_names=["lines"])
    return po
