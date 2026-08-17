"""
RBAC core: roles, permissions (module -> resource -> action), and the
join tables linking roles<->permissions and users<->roles.

Seeded roles (workbook 'Roles & Permissions'): SuperAdmin, CSR, MX Manager,
BX Manager, Validator, Supervisor, Meter Reader, Consumer, Property Manager,
Field Technician. See app/services/seed.py.
"""
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin

PERMISSION_ACTIONS = ("view", "create", "edit", "delete", "approve", "execute", "export", "download")


class Permission(UUIDPKMixin, Base):
    """Global catalogue of module -> resource -> action. Not tenant-scoped."""

    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("module", "resource", "action", name="uq_permission"),)

    module: Mapped[str] = mapped_column(String(50), nullable=False)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Role(UUIDPKMixin, TimestampMixin, Base):
    """
    tenant_id is nullable: SuperAdmin's platform role has tenant_id=None.
    Every other role belongs to a tenant (cloned from the system defaults
    at utility onboarding) so tenants can add custom roles later.
    """

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),)

    tenant_id: Mapped[Optional[str]] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # seeded, non-deletable


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[str] = mapped_column(ForeignKey("permissions.id"), primary_key=True)


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), primary_key=True)
