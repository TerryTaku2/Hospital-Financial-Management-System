from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import AuditAction


class AuditLogOut(BaseModel):
    id: int
    actor_id: int | None
    branch_id: int | None
    table_name: str
    record_id: int
    action: AuditAction
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}
