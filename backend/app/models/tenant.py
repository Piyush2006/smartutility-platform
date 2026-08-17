from typing import Optional
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin

TENANT_STATUSES = ("active", "suspended")


class Tenant(UUIDPKMixin, TimestampMixin, Base):
    """
    A Tenant == a Utility (workbook 'Onboarding Data' -> Utility fields).
    Section 7 validations enforced in app/schemas/tenant.py.
    """

    __tablename__ = "tenants"

    # Utility identity
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    date_format: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    e_transfer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hst_gst_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
