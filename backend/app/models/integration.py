import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantOwnedMixin, TimestampMixin, UUIDPKMixin


class SmartMeterOem(UUIDPKMixin, Base):
    """Platform-level catalogue (workbook §24), seeded once, not tenant-owned."""

    __tablename__ = "smart_meter_oems"
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    utility_services: Mapped[str] = mapped_column(String(255), nullable=False)
    highlights: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    integration_resources: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    links: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)


class IntegrationConfig(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    """Per-tenant integration abstraction. provider='mock_smart_meter' is
    the only implemented provider -- CLAUDE.md explicitly asks for an
    abstraction + one mock, not real OEM integrations."""

    __tablename__ = "integration_configs"
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    smart_meter_oem_id: Mapped[Optional[str]] = mapped_column(ForeignKey("smart_meter_oems.id"), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    last_sync_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # ok|failed
