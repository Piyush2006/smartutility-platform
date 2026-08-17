"""Single write path for audit_logs (CLAUDE.md #26). Call after a
successful commit of the change being recorded."""
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_audit(
    db: Session,
    *,
    tenant_id: Optional[str],
    user_id: Optional[str],
    module: str,
    entity: str,
    entity_id: Optional[str],
    action: str,
    old_value: Optional[dict[str, Any]] = None,
    new_value: Optional[dict[str, Any]] = None,
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            module=module,
            entity=entity,
            entity_id=entity_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
        )
    )
    db.commit()
