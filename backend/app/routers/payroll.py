from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import get_current_user, require_role, verify_csrf
from app.models.enums import RoleEnum
from app.models.payroll import PayrollRun, PayslipItem
from app.models.user import User
from app.schemas.payroll import PayrollPayRequest, PayrollRunCreate, PayrollRunOut, PayslipItemOut, PayslipItemUpdate
from app.services.payroll_service import (
    create_payroll_run,
    finalize_payroll_run,
    pay_payroll_run,
    update_payslip_item,
    void_payroll_run,
)
from app.services.posting_service import PostingError

router = APIRouter(
    prefix="/api/payroll-runs",
    tags=["payroll"],
    dependencies=[Depends(verify_csrf), Depends(require_role(RoleEnum.ADMIN, RoleEnum.ACCOUNTANT))],
)


async def _get_run_or_404(db: AsyncSession, run_id: int) -> PayrollRun:
    run = await db.get(PayrollRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payroll run not found")
    return run


async def _get_item_or_404(db: AsyncSession, run_id: int, item_id: int) -> PayslipItem:
    item = (
        await db.execute(
            select(PayslipItem).where(PayslipItem.id == item_id, PayslipItem.payroll_run_id == run_id)
        )
    ).scalars().first()
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payslip item not found")
    return item


@router.get("", response_model=list[PayrollRunOut])
async def list_payroll_runs(
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[PayrollRun]:
    stmt = select(PayrollRun).order_by(PayrollRun.id.desc())
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(PayrollRun.branch_id == effective_branch_id)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{run_id}", response_model=PayrollRunOut)
async def get_payroll_run(
    run_id: int, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> PayrollRun:
    run = await _get_run_or_404(db, run_id)
    scope.check_access(run.branch_id)
    return run


@router.post("", response_model=PayrollRunOut)
async def create_payroll_run_endpoint(
    run_in: PayrollRunCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> PayrollRun:
    scope.check_write(run_in.branch_id)
    try:
        run = await create_payroll_run(db, run_in, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(run, attribute_names=["items"])
    return run


@router.patch("/{run_id}/items/{item_id}", response_model=PayslipItemOut)
async def update_payslip_item_endpoint(
    run_id: int,
    item_id: int,
    item_in: PayslipItemUpdate,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> PayslipItem:
    run = await _get_run_or_404(db, run_id)
    scope.check_write(run.branch_id)
    item = await _get_item_or_404(db, run_id, item_id)
    try:
        item = await update_payslip_item(
            db, run, item, allowances=item_in.allowances, deductions=item_in.deductions, notes=item_in.notes
        )
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/{run_id}/finalize", response_model=PayrollRunOut)
async def finalize_payroll_run_endpoint(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> PayrollRun:
    run = await _get_run_or_404(db, run_id)
    scope.check_write(run.branch_id)
    try:
        run = await finalize_payroll_run(db, run, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(run, attribute_names=["items"])
    return run


@router.post("/{run_id}/pay", response_model=PayrollRunOut)
async def pay_payroll_run_endpoint(
    run_id: int,
    pay_in: PayrollPayRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> PayrollRun:
    run = await _get_run_or_404(db, run_id)
    scope.check_write(run.branch_id)
    try:
        run = await pay_payroll_run(db, run, user, pay_in.method)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(run, attribute_names=["items"])
    return run


@router.post("/{run_id}/void", response_model=PayrollRunOut)
async def void_payroll_run_endpoint(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
) -> PayrollRun:
    run = await _get_run_or_404(db, run_id)
    scope.check_write(run.branch_id)
    try:
        run = await void_payroll_run(db, run, user)
    except PostingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    await db.refresh(run, attribute_names=["items"])
    return run
