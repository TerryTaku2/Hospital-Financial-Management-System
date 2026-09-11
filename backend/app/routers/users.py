from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import require_role, verify_csrf
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.auth import AdminResetPasswordRequest, UserCreate, UserOut
from app.security import hash_password

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    dependencies=[Depends(verify_csrf), Depends(require_role(RoleEnum.ADMIN))],
)


@router.get("", response_model=list[UserOut])
async def list_users(
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[User]:
    stmt = select(User)
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(User.branch_id == effective_branch_id)
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=UserOut)
async def create_user(
    user_in: UserCreate, db: AsyncSession = Depends(get_db), scope: BranchScope = Depends(get_branch_scope)
) -> User:
    scope.check_write(user_in.branch_id)
    user = User(
        branch_id=user_in.branch_id,
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    payload: AdminResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> dict[str, bool]:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    scope.check_write(user.branch_id)
    user.hashed_password = hash_password(payload.new_password)
    await db.commit()
    return {"ok": True}
