from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.branch import Branch
from app.models.user import User


@dataclass
class BranchScope:
    """Only the main/head-office branch can see across branches. Everyone
    else is locked to their own branch_id, on both reads and writes."""

    user: User
    can_see_all: bool

    def resolve_list_filter(self, requested_branch_id: int | None) -> int | None:
        """Branch id to filter a list query by, or None to mean 'no filter'
        (only ever returned for a main-branch user who didn't ask for one)."""
        if self.can_see_all:
            return requested_branch_id
        return self.user.branch_id

    def check_access(self, record_branch_id: int) -> None:
        if not self.can_see_all and record_branch_id != self.user.branch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")

    def check_write(self, target_branch_id: int) -> None:
        if not self.can_see_all and target_branch_id != self.user.branch_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot act on another branch's data")


async def is_main_branch_user(db: AsyncSession, user: User) -> bool:
    main_branch_id = (await db.execute(select(Branch.id).where(Branch.is_main.is_(True)))).scalar_one_or_none()
    return main_branch_id is not None and user.branch_id == main_branch_id


async def get_branch_scope(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> BranchScope:
    return BranchScope(user=user, can_see_all=await is_main_branch_user(db, user))
