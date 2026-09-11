import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import require_role, verify_csrf
from app.models.employee import Employee
from app.models.enums import RoleEnum
from app.schemas.employee import EmployeeCreate, EmployeeOut, EmployeeUpdate

router = APIRouter(
    prefix="/api/employees",
    tags=["employees"],
    dependencies=[Depends(verify_csrf), Depends(require_role(RoleEnum.ADMIN, RoleEnum.ACCOUNTANT))],
)


def _generate_employee_number() -> str:
    return f"EMP-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3).upper()}"


async def _get_employee_or_404(db: AsyncSession, employee_id: int) -> Employee:
    employee = await db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    return employee


@router.get("", response_model=list[EmployeeOut])
async def list_employees(
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[Employee]:
    stmt = select(Employee).order_by(Employee.full_name)
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(Employee.branch_id == effective_branch_id)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee(
    employee_id: int, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> Employee:
    employee = await _get_employee_or_404(db, employee_id)
    scope.check_access(employee.branch_id)
    return employee


@router.post("", response_model=EmployeeOut)
async def create_employee(
    employee_in: EmployeeCreate, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> Employee:
    scope.check_write(employee_in.branch_id)
    employee = Employee(employee_number=_generate_employee_number(), **employee_in.model_dump())
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return employee


@router.patch("/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: int,
    employee_in: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> Employee:
    employee = await _get_employee_or_404(db, employee_id)
    scope.check_write(employee.branch_id)
    for field, value in employee_in.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    await db.commit()
    await db.refresh(employee)
    return employee
