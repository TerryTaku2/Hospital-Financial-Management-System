from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.enums import CashVoucherStatus, RoleEnum
from app.models.user import User
from app.models.voucher import CashVoucher
from app.schemas.voucher import CashVoucherCreate, CashVoucherOut, VoucherReason
from app.services.posting_service import PostingError
from app.services.voucher_service import (
    cancel_voucher,
    confirm_voucher,
    create_voucher,
    disburse_voucher,
    reject_voucher,
)

router = APIRouter(prefix="/api/cash-vouchers", tags=["cash-vouchers"], dependencies=[Depends(verify_csrf)])

CAN_PREPARE_VOUCHER = require_role(RoleEnum.ADMIN, RoleEnum.ACCOUNTANT, RoleEnum.ACCOUNTS_CLERK)
CAN_CONFIRM_VOUCHER = require_role(RoleEnum.ACCOUNTANT)
CAN_DISBURSE_VOUCHER = require_role(RoleEnum.ACCOUNTS_CLERK)


async def _get_or_404(db: AsyncSession, voucher_id: int) -> CashVoucher:
    voucher = await db.get(CashVoucher, voucher_id)
    if voucher is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cash voucher not found")
    return voucher


@router.get("", response_model=list[CashVoucherOut])
async def list_vouchers(
    status_filter: CashVoucherStatus | None = None,
    purchase_order_id: int | None = None,
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[CashVoucher]:
    stmt = select(CashVoucher).order_by(CashVoucher.id.desc())
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(CashVoucher.branch_id == effective_branch_id)
    if status_filter is not None:
        stmt = stmt.where(CashVoucher.status == status_filter)
    if purchase_order_id is not None:
        stmt = stmt.where(CashVoucher.purchase_order_id == purchase_order_id)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{voucher_id}", response_model=CashVoucherOut)
async def get_voucher(
    voucher_id: int, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> CashVoucher:
    voucher = await _get_or_404(db, voucher_id)
    scope.check_access(voucher.branch_id)
    return voucher


@router.post("", response_model=CashVoucherOut, dependencies=[Depends(CAN_PREPARE_VOUCHER)])
async def create_voucher_endpoint(
    voucher_in: CashVoucherCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> CashVoucher:
    scope.check_write(voucher_in.branch_id)
    try:
        voucher = await create_voucher(db, voucher_in, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(voucher)
    return voucher


@router.post("/{voucher_id}/confirm", response_model=CashVoucherOut, dependencies=[Depends(CAN_CONFIRM_VOUCHER)])
async def confirm_voucher_endpoint(
    voucher_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> CashVoucher:
    voucher = await _get_or_404(db, voucher_id)
    scope.check_access(voucher.branch_id)
    scope.check_write(voucher.branch_id)
    try:
        voucher = await confirm_voucher(db, voucher, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(voucher)
    return voucher


@router.post("/{voucher_id}/reject", response_model=CashVoucherOut, dependencies=[Depends(CAN_CONFIRM_VOUCHER)])
async def reject_voucher_endpoint(
    voucher_id: int,
    body: VoucherReason,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> CashVoucher:
    voucher = await _get_or_404(db, voucher_id)
    scope.check_access(voucher.branch_id)
    scope.check_write(voucher.branch_id)
    try:
        voucher = await reject_voucher(db, voucher, user, body.reason)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(voucher)
    return voucher


@router.post("/{voucher_id}/disburse", response_model=CashVoucherOut, dependencies=[Depends(CAN_DISBURSE_VOUCHER)])
async def disburse_voucher_endpoint(
    voucher_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> CashVoucher:
    voucher = await _get_or_404(db, voucher_id)
    scope.check_access(voucher.branch_id)
    scope.check_write(voucher.branch_id)
    try:
        voucher = await disburse_voucher(db, voucher, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(voucher)
    return voucher


@router.post("/{voucher_id}/cancel", response_model=CashVoucherOut, dependencies=[Depends(CAN_PREPARE_VOUCHER)])
async def cancel_voucher_endpoint(
    voucher_id: int,
    body: VoucherReason,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> CashVoucher:
    voucher = await _get_or_404(db, voucher_id)
    scope.check_access(voucher.branch_id)
    scope.check_write(voucher.branch_id)
    try:
        voucher = await cancel_voucher(db, voucher, user, body.reason)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(voucher)
    return voucher
