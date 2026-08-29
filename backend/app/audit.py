from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.enums import AuditAction


async def write_audit_log(
    db: AsyncSession,
    *,
    actor_id: int | None,
    branch_id: int | None,
    table_name: str,
    record_id: int,
    action: AuditAction,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            branch_id=branch_id,
            table_name=table_name,
            record_id=record_id,
            action=action,
            before=before,
            after=after,
        )
    )
