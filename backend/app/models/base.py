import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPKMixin:
    id: Mapped[str] = mapped_column(primary_key=True, default=gen_uuid)


class TimestampMixin:
    # Client-side `default` (Python, microsecond precision) takes priority
    # over `server_default` whenever the ORM performs the insert -- needed
    # because SQLite's CURRENT_TIMESTAMP only has 1-second resolution,
    # which made rows inserted in the same second (e.g. two bill runs for
    # the same consumer generated back-to-back) impossible to order
    # correctly by created_at. server_default remains as a DDL-level
    # fallback for any insert that bypasses the ORM.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), onupdate=_utcnow
    )


class TenantOwnedMixin:
    """
    Mix into every tenant-owned entity. tenant_id must be enforced server-side
    on every query -- see app/api/deps.py::tenant_scope.
    """

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
