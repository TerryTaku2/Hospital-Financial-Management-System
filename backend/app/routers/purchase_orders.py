from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.enums import RoleEnum
from app.models.procurement import PurchaseOrder, SupplierPayment
from app.models.user import User
from app.schemas.procurement import PurchaseOrderCreate, PurchaseOrderOut, SupplierPaymentCreate, SupplierPaymentOut
from app.services.posting_service import PostingError
from app.services.procurement_service import cancel_purchase_order, create_purchase_order, receive_purchase_order, record_supplier_payment

router = APIRouter(prefix="/api/purchase-orders", tags=["purchase-orders"], dependencies=[Depends(verify_csrf)])

CAN_MANAGE_PO = require_role(RoleEnum.ADMIN, RoleEnum.CASHIER, RoleEnum.ACCOUNTANT)
CAN_PAY_SUPPLIER = require_role(RoleEnum.ADMIN, RoleEnum.ACCOUNTANT)


class CancelRequest(BaseModel):
    reason: str


async def _get_po_or_404(db: AsyncSession, po_id: int) -> PurchaseOrder:
    po = await db.get(PurchaseOrder, po_id)
    if po is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order not found")
    return po


@router.get("", response_model=list[PurchaseOrderOut])
async def list_purchase_orders(
    supplier_id: int | None = None,
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[PurchaseOrder]:
    stmt = select(PurchaseOrder).order_by(PurchaseOrder.id.desc())
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(PurchaseOrder.branch_id == effective_branch_id)
    if supplier_id is not None:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{po_id}", response_model=PurchaseOrderOut)
async def get_purchase_order(
    po_id: int, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> PurchaseOrder:
    po = await _get_po_or_404(db, po_id)
    scope.check_access(po.branch_id)
    return po


@router.post("", response_model=PurchaseOrderOut, dependencies=[Depends(CAN_MANAGE_PO)])
async def create_purchase_order_endpoint(
    po_in: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> PurchaseOrder:
    scope.check_write(po_in.branch_id)
    try:
        po = await create_purchase_order(db, po_in, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(po, attribute_names=["lines"])
    return po


@router.post("/{po_id}/receive", response_model=PurchaseOrderOut, dependencies=[Depends(CAN_MANAGE_PO)])
async def receive_purchase_order_endpoint(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> PurchaseOrder:
    po = await _get_po_or_404(db, po_id)
    scope.check_access(po.branch_id)
    try:
        po = await receive_purchase_order(db, po, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(po, attribute_names=["lines"])
    return po


@router.post("/{po_id}/cancel", response_model=PurchaseOrderOut, dependencies=[Depends(CAN_MANAGE_PO)])
async def cancel_purchase_order_endpoint(
    po_id: int,
    cancel_in: CancelRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> PurchaseOrder:
    po = await _get_po_or_404(db, po_id)
    scope.check_access(po.branch_id)
    try:
        po = await cancel_purchase_order(db, po, user, cancel_in.reason)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(po, attribute_names=["lines"])
    return po


@router.get("/{po_id}/payments", response_model=list[SupplierPaymentOut])
async def list_supplier_payments(
    po_id: int, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> list[SupplierPayment]:
    po = await _get_po_or_404(db, po_id)
    scope.check_access(po.branch_id)
    stmt = select(SupplierPayment).where(SupplierPayment.purchase_order_id == po_id).order_by(SupplierPayment.id.desc())
    return list((await db.execute(stmt)).scalars().all())


@router.post("/{po_id}/pay", response_model=SupplierPaymentOut, dependencies=[Depends(CAN_PAY_SUPPLIER)])
async def pay_supplier_endpoint(
    po_id: int,
    payment_in: SupplierPaymentCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
):
    po = await _get_po_or_404(db, po_id)
    scope.check_access(po.branch_id)
    if payment_in.purchase_order_id != po_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "purchase_order_id does not match the URL")
    try:
        payment, _created = await record_supplier_payment(db, payment_in, user, idempotency_key)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(payment)
    return payment
