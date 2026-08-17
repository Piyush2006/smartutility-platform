import datetime
from typing import Optional

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantOwnedMixin, TimestampMixin, UUIDPKMixin

CONSUMER_STATUSES = ("active", "inactive")


class Consumer(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    """Workbook §11 fields, exact names."""

    __tablename__ = "consumers"

    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    contact_no: Mapped[str] = mapped_column(String(20), nullable=False)
    email_address: Mapped[str] = mapped_column(String(255), nullable=False)
    ssn: Mapped[str] = mapped_column(String(11), nullable=False)  # masked/stored as XXX-XX-XXXX
    id_document_url: Mapped[str] = mapped_column(String(500), nullable=False)
    premise_id: Mapped[str] = mapped_column(ForeignKey("premises.id"), nullable=False)
    service_address: Mapped[str] = mapped_column(String(250), nullable=False)
    billing_address: Mapped[str] = mapped_column(String(250), nullable=False)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"), nullable=False)
    activation_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    meter_id: Mapped[str] = mapped_column(ForeignKey("meters.id"), nullable=False, unique=True)
    first_meter_reading: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    first_meter_reading_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="active")

    # Property Manager scoping (§4/§23): a manager can be assigned specific
    # consumers via this optional link to the managing user.
    property_manager_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Consumer login: a User row (is_superadmin=False, tenant-scoped, role
    # "Consumer") is created alongside and linked here for portal access.
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True, unique=True)
