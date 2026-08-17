import datetime
from typing import Optional

from sqlalchemy import JSON, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantOwnedMixin, TimestampMixin, UUIDPKMixin

READING_STATUSES = ("Received", "V1", "V2", "Revisit", "Completed")
READING_SOURCES = ("manual", "upload", "smart_meter")


class MeterReadingImport(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    """One CSV/XLSX upload batch. Original file is kept -- never lose
    uploaded data, even if individual rows fail validation."""

    __tablename__ = "meter_reading_imports"

    meter_run_id: Mapped[Optional[str]] = mapped_column(ForeignKey("meter_runs.id"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    total_rows: Mapped[int] = mapped_column(default=0)
    valid_rows: Mapped[int] = mapped_column(default=0)
    invalid_rows: Mapped[int] = mapped_column(default=0)


class ImportRow(UUIDPKMixin, TenantOwnedMixin, Base):
    """Raw + parsed content of one row from an import, kept regardless of
    validity so nothing uploaded is ever discarded."""

    __tablename__ = "import_rows"

    import_id: Mapped[str] = mapped_column(ForeignKey("meter_reading_imports.id"), nullable=False)
    row_number: Mapped[int] = mapped_column(nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_valid: Mapped[bool] = mapped_column(default=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    meter_reading_id: Mapped[Optional[str]] = mapped_column(ForeignKey("meter_readings.id"), nullable=True)


class MeterReading(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "meter_readings"

    meter_id: Mapped[str] = mapped_column(ForeignKey("meters.id"), nullable=False)
    meter_run_id: Mapped[Optional[str]] = mapped_column(ForeignKey("meter_runs.id"), nullable=True)
    read_cycle_id: Mapped[Optional[str]] = mapped_column(ForeignKey("read_cycles.id"), nullable=True)

    previous_reading: Mapped[Optional[float]] = mapped_column(Numeric(14, 3), nullable=True)
    previous_reading_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    current_reading: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    current_reading_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)

    source: Mapped[str] = mapped_column(String(20), default="manual")  # READING_SOURCES
    status: Mapped[str] = mapped_column(String(20), default="Received")  # READING_STATUSES
    is_duplicate: Mapped[bool] = mapped_column(default=False)
