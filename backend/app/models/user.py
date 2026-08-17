from typing import Optional
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class User(UUIDPKMixin, TimestampMixin, Base):
    """
    tenant_id is nullable: platform users (SuperAdmin) have tenant_id=None.
    Every other user (Utility Admin, CSR, Consumer, ...) belongs to exactly
    one tenant.
    """

    __tablename__ = "users"

    tenant_id: Mapped[Optional[str]] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Property Manager scoping (workbook: "assigned consumer data only").
    # Populated in the Consumer module phase; kept here so the FK/table shape
    # doesn't need to change later.
