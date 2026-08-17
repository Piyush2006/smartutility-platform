from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantOwnedMixin, TimestampMixin, UUIDPKMixin


class UtilityService(UUIDPKMixin, Base):
    """Global catalogue (Water/Sewer/Gas/Electricity, ...). Never hard-code
    services in business logic -- always join through this table."""

    __tablename__ = "utility_services"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)


class TenantService(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    """Per-tenant on/off toggle for a catalogue service (workbook §7)."""

    __tablename__ = "tenant_services"
    __table_args__ = (UniqueConstraint("tenant_id", "utility_service_id", name="uq_tenant_service"),)

    utility_service_id: Mapped[str] = mapped_column(ForeignKey("utility_services.id"), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
