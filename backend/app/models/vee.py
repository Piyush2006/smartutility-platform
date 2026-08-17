import datetime
from typing import Optional

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantOwnedMixin, TimestampMixin, UUIDPKMixin

VEE_RULE_TYPES = ("No Reading", "Threshold Alert")  # extensible -- see VeeRule.rule_type
VEE_INTERVALS = ("15 min", "30 min", "1 hour", "6 hours", "12 hours", "24 hours")


class VeeRule(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    """Workbook §16. rule_type is one of VEE_RULE_TYPES or a tenant-defined
    addition -- 'Allow additional rule types through configuration.'"""

    __tablename__ = "vee_rules"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    utility_service_id: Mapped[str] = mapped_column(ForeignKey("utility_services.id"), nullable=False)
    read_type: Mapped[str] = mapped_column(String(20), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # rule_type-specific parameters, e.g. {"max_days_without_reading": 45} or
    # {"min_units": 0, "max_units": 5000} for a threshold check.
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class VeeConfig(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "vee_configs"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    utility_service_id: Mapped[str] = mapped_column(ForeignKey("utility_services.id"), nullable=False)
    read_type: Mapped[str] = mapped_column(String(20), nullable=False)


class VeeConfigRule(Base):
    __tablename__ = "vee_config_rules"
    vee_config_id: Mapped[str] = mapped_column(ForeignKey("vee_configs.id"), primary_key=True)
    vee_rule_id: Mapped[str] = mapped_column(ForeignKey("vee_rules.id"), primary_key=True)


class VeeSchedule(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "vee_schedules"

    vee_config_id: Mapped[str] = mapped_column(ForeignKey("vee_configs.id"), nullable=False)
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    repetition_interval: Mapped[str] = mapped_column(String(20), nullable=False)  # VEE_INTERVALS
    end_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)


class ValidationEvent(UUIDPKMixin, TenantOwnedMixin, Base):
    """One VEE evaluation of one meter_reading against one rule -- powers
    the V1/V2/Revisit/Completed breakdown (workbook §17)."""

    __tablename__ = "validation_events"

    meter_reading_id: Mapped[str] = mapped_column(ForeignKey("meter_readings.id"), nullable=False)
    vee_rule_id: Mapped[str] = mapped_column(ForeignKey("vee_rules.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(10), nullable=False)  # "V1" | "V2"
    passed: Mapped[bool] = mapped_column(nullable=False)
    message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    evaluated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
