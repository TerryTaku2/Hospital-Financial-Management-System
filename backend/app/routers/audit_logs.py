from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branch_scope import BranchScope, get_branch_scope
from app.database import get_db
from app.dependencies import require_role
from app.models.audit_log import AuditLog
from app.models.enums import RoleEnum
from app.schemas.audit_log import AuditLogOut

router = APIRouter(
    prefix="/api/audit-logs",
    tags=["audit-logs"],
    dependencies=[Depends(require_role(RoleEnum.ADMIN, RoleEnum.AUDITOR))],
)


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(
    table_name: str | None = None,
    branch_id: int | None = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(get_branch_scope),
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    effective_branch_id = scope.resolve_list_filter(branch_id)
    if effective_branch_id is not None:
        stmt = stmt.where(AuditLog.branch_id == effective_branch_id)
    if table_name is not None:
        stmt = stmt.where(AuditLog.table_name == table_name)
    return list((await db.execute(stmt)).scalars().all())
