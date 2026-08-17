"""
Utility onboarding (CLAUDE.md §6): creates (1) tenant, (2) cloned system
roles + permissions, (3) the Utility Admin user, (4) default config records.
No email infrastructure exists yet, so the Utility Admin's one-time
temporary password is returned directly in the API response (SuperAdmin
relays it out-of-band) rather than emailed.
"""
import secrets
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.rbac import Role, RolePermission, UserRole
from app.models.rbac import Permission
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantCreate
from app.services.audit import record_audit
from app.services.rbac_catalog import PERMISSIONS, ROLE_PERMISSION_DEFAULTS, SYSTEM_ROLES


@dataclass
class OnboardingResult:
    tenant: Tenant
    admin_user: User
    temp_password: str


def _permission_lookup(db: Session) -> dict[tuple[str, str, str], Permission]:
    return {(p.module, p.resource, p.action): p for p in db.query(Permission).all()}


def onboard_utility(db: Session, payload: TenantCreate, *, actor_user_id: str) -> OnboardingResult:
    tenant = Tenant(
        name=payload.name,
        phone_no=payload.phone_no,
        address=payload.address,
        website=payload.website,
        email=payload.email,
        currency=payload.currency,
        timezone=payload.timezone,
        date_format=payload.date_format,
        e_transfer=payload.e_transfer,
        hst_gst_no=payload.hst_gst_no,
        status="active",
    )
    db.add(tenant)
    db.flush()

    perms = _permission_lookup(db)
    roles: dict[str, Role] = {}
    for role_def in SYSTEM_ROLES:
        role = Role(tenant_id=tenant.id, name=role_def["name"], description=role_def["description"], is_system=True)
        db.add(role)
        db.flush()
        roles[role_def["name"]] = role
        for module, resource, action in ROLE_PERMISSION_DEFAULTS.get(role_def["name"], []):
            perm = perms.get((module, resource, action))
            if perm:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    temp_password = secrets.token_urlsafe(9)
    admin_user = User(
        tenant_id=tenant.id,
        email=payload.admin_email,
        full_name=payload.admin_full_name,
        password_hash=hash_password(temp_password),
    )
    db.add(admin_user)
    db.flush()
    db.add(UserRole(user_id=admin_user.id, role_id=roles["Utility Admin"].id))

    db.commit()
    db.refresh(tenant)
    db.refresh(admin_user)

    record_audit(
        db, tenant_id=tenant.id, user_id=actor_user_id, module="platform", entity="Tenant",
        entity_id=tenant.id, action="create", new_value={"name": tenant.name, "admin_email": admin_user.email},
    )

    return OnboardingResult(tenant=tenant, admin_user=admin_user, temp_password=temp_password)
