from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.billing import Deposit
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.billing import DepositApply, DepositCreate, DepositOut, RefundCreate, RefundOut
from app.services.deposit_service import apply_deposit, refund_deposit, take_deposit
from app.services.posting_service import PostingError

router = APIRouter(prefix="/api/deposits", tags=["deposits"], dependencies=[Depends(verify_csrf)])

CAN_HANDLE_DEPOSITS = require_role(RoleEnum.ADMIN, RoleEnum.CASHIER, RoleEnum.ACCOUNTANT)


async def _get_deposit_or_404(db: AsyncSession, deposit_id: int) -> Deposit:
    deposit = await db.get(Deposit, deposit_id)
    if deposit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deposit not found")
    return deposit


@router.get("", response_model=list[DepositOut])
async def list_deposits(
    patient_id: int | None = None,
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[Deposit]:
    stmt = select(Deposit).order_by(Deposit.id.desc())
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(Deposit.branch_id == effective_branch_id)
    if patient_id is not None:
        stmt = stmt.where(Deposit.patient_id == patient_id)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{deposit_id}", response_model=DepositOut)
async def get_deposit(
    deposit_id: int, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> Deposit:
    deposit = await _get_deposit_or_404(db, deposit_id)
    scope.check_access(deposit.branch_id)
    return deposit


@router.post("", response_model=DepositOut, dependencies=[Depends(CAN_HANDLE_DEPOSITS)])
async def create_deposit(
    deposit_in: DepositCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> Deposit:
    scope.check_write(deposit_in.branch_id)
    try:
        deposit, _created = await take_deposit(db, deposit_in, user, idempotency_key)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(deposit)
    return deposit


@router.post("/{deposit_id}/apply", response_model=DepositOut, dependencies=[Depends(CAN_HANDLE_DEPOSITS)])
async def apply_deposit_endpoint(
    deposit_id: int,
    apply_in: DepositApply,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> Deposit:
    deposit = await _get_deposit_or_404(db, deposit_id)
    scope.check_access(deposit.branch_id)
    try:
        deposit = await apply_deposit(db, deposit, apply_in, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(deposit)
    return deposit


@router.post("/{deposit_id}/refund", response_model=RefundOut, dependencies=[Depends(CAN_HANDLE_DEPOSITS)])
async def refund_deposit_endpoint(
    deposit_id: int,
    refund_in: RefundCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
):
    deposit = await _get_deposit_or_404(db, deposit_id)
    scope.check_access(deposit.branch_id)
    try:
        refund, _created = await refund_deposit(db, deposit, refund_in, user, idempotency_key)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(refund)
    return refund
