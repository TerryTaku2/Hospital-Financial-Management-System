from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import require_role, verify_csrf
from app.models.branch import Branch
from app.models.enums import RoleEnum
from app.schemas.branch import BranchCreate, BranchOut

router = APIRouter(prefix="/api/branches", tags=["branches"], dependencies=[Depends(verify_csrf)])


@router.get("", response_model=list[BranchOut])
async def list_branches(db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)) -> list[Branch]:
    stmt = select(Branch)
    if not scope.can_see_all:
        stmt = stmt.where(Branch.id == scope.user.branch_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=BranchOut, dependencies=[Depends(require_role(RoleEnum.ADMIN))])
async def create_branch(
    branch_in: BranchCreate, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> Branch:
    if not scope.can_see_all:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the main branch can create new branches")
    branch = Branch(**branch_in.model_dump())
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return branch
