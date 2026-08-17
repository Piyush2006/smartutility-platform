"""
Tenant staff user management + role assignment (CLAUDE.md §4). Consumer
Portal logins are managed from the Consumers screen instead -- this page
is for internal staff (CSR, MX Manager, BX Manager, Validator, Supervisor,
Meter Reader, Property Manager, Field Technician, additional Utility
Admins).
"""
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_tenant_id, require_permission
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_invite_token, hash_password
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.user import (
    PermissionSummaryOut,
    RoleCreate,
    RoleDetailOut,
    RoleSummaryOut,
    RoleUpdate,
    TenantUserCreate,
    TenantUserOut,
    TenantUserUpdate,
    UserInviteOut,
)
from app.services.audit import record_audit
from app.services.email_service import send_invite_email

router = APIRouter(tags=["users"])


def _roles_for_user(db: Session, user_id: str) -> list[Role]:
    stmt = select(Role).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
    return list(db.execute(stmt).scalars())


def _user_out(db: Session, user: User) -> TenantUserOut:
    roles = _roles_for_user(db, user.id)
    return TenantUserOut(
        id=user.id, full_name=user.full_name, email=user.email, is_active=user.is_active,
        roles=[RoleSummaryOut.model_validate(r) for r in roles],
    )


@router.get("/users", response_model=list[TenantUserOut])
def list_users(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("users", "users", "view"))):
    """Staff only -- users whose sole role is Consumer are managed from
    /consumers instead."""
    tenant_users = list(db.execute(select(User).where(User.tenant_id == tenant_id)).scalars())
    out = []
    for user in tenant_users:
        roles = _roles_for_user(db, user.id)
        if roles and all(r.name == "Consumer" for r in roles):
            continue
        out.append(TenantUserOut(id=user.id, full_name=user.full_name, email=user.email, is_active=user.is_active, roles=[RoleSummaryOut.model_validate(r) for r in roles]))
    return out


@router.get("/users/{user_id}", response_model=TenantUserOut)
def get_user(user_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("users", "users", "view"))):
    user = db.get(User, user_id)
    if user is None or user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_out(db, user)


@router.post("/users", response_model=UserInviteOut, status_code=status.HTTP_201_CREATED)
def invite_user(
    payload: TenantUserCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("users", "users", "create")),
):
    role = db.get(Role, payload.role_id)
    if role is None or (role.tenant_id != tenant_id and role.tenant_id is not None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select a valid role.")
    if db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists.")

    # Locked with an unrevealed random password -- the account is unusable
    # until the invite link below is used to set a real one.
    locked_password = secrets.token_urlsafe(32)
    user = User(tenant_id=tenant_id, email=payload.email, full_name=payload.full_name, password_hash=hash_password(locked_password))
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    db.refresh(user)

    tenant = db.get(Tenant, tenant_id)
    invite_token = create_invite_token(user_id=user.id)
    invite_link = f"{settings.FRONTEND_URL}/set-password?token={invite_token}"
    email_sent = send_invite_email(to=user.email, full_name=user.full_name, invite_link=invite_link, tenant_name=tenant.name if tenant else "your utility")

    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="users", entity="User", entity_id=user.id, action="create", new_value={"email": user.email, "role": role.name, "email_sent": email_sent})
    return UserInviteOut(user=_user_out(db, user), email_sent=email_sent, invite_link=invite_link)


@router.patch("/users/{user_id}", response_model=TenantUserOut)
def update_user(
    user_id: str, payload: TenantUserUpdate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("users", "users", "edit")),
):
    user = db.get(User, user_id)
    if user is None or user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active

    if payload.role_id is not None:
        role = db.get(Role, payload.role_id)
        if role is None or (role.tenant_id != tenant_id and role.tenant_id is not None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select a valid role.")
        for existing in db.execute(select(UserRole).where(UserRole.user_id == user.id)).scalars():
            db.delete(existing)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))

    db.commit()
    db.refresh(user)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="users", entity="User", entity_id=user.id, action="edit")
    return _user_out(db, user)


# ---- Permission catalogue (for the role-builder's permission picker) ------

@router.get("/permissions", response_model=list[PermissionSummaryOut])
def list_permissions(db: Session = Depends(get_db), _=Depends(require_permission("users", "users", "view"))):
    """Global catalogue, not tenant-scoped -- every tenant can build roles
    out of the same module/resource/action set (see app/services/rbac_catalog.py)."""
    permissions = list(db.execute(select(Permission).where(Permission.module != "platform")).scalars())
    return [PermissionSummaryOut.model_validate(p) for p in permissions]


# ---- Roles: assign existing roles from the Users tab, or build custom ones ----

def _role_detail_out(db: Session, role: Role) -> RoleDetailOut:
    stmt = select(Permission).join(RolePermission, RolePermission.permission_id == Permission.id).where(RolePermission.role_id == role.id)
    permissions = list(db.execute(stmt).scalars())
    return RoleDetailOut(
        id=role.id, name=role.name, description=role.description, is_system=role.is_system,
        permissions=[PermissionSummaryOut.model_validate(p) for p in permissions],
    )


@router.get("/roles", response_model=list[RoleSummaryOut])
def list_roles(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("users", "users", "view"))):
    roles = list(db.execute(select(Role).where(Role.tenant_id == tenant_id)).scalars())
    return [RoleSummaryOut.model_validate(r) for r in roles]


@router.get("/roles/{role_id}", response_model=RoleDetailOut)
def get_role(role_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("users", "users", "view"))):
    role = db.get(Role, role_id)
    if role is None or role.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return _role_detail_out(db, role)


@router.post("/roles", response_model=RoleDetailOut, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("users", "users", "create")),
):
    existing = db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name == payload.name)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A role with this name already exists.")
    permissions = list(db.execute(select(Permission).where(Permission.id.in_(payload.permission_ids))).scalars())
    if len(permissions) != len(set(payload.permission_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more selected permissions are invalid.")

    role = Role(tenant_id=tenant_id, name=payload.name, description=payload.description, is_system=False)
    db.add(role)
    db.flush()
    for perm in permissions:
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.commit()
    db.refresh(role)

    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="users", entity="Role", entity_id=role.id, action="create", new_value={"name": role.name, "permission_count": len(permissions)})
    return _role_detail_out(db, role)


@router.patch("/roles/{role_id}", response_model=RoleDetailOut)
def update_role(
    role_id: str, payload: RoleUpdate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("users", "users", "edit")),
):
    role = db.get(Role, role_id)
    if role is None or role.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="System roles from the workbook can't be edited -- create a custom role instead.")

    if payload.name is not None:
        role.name = payload.name
    if payload.description is not None:
        role.description = payload.description
    if payload.permission_ids is not None:
        permissions = list(db.execute(select(Permission).where(Permission.id.in_(payload.permission_ids))).scalars())
        if len(permissions) != len(set(payload.permission_ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more selected permissions are invalid.")
        for existing in db.execute(select(RolePermission).where(RolePermission.role_id == role.id)).scalars():
            db.delete(existing)
        db.flush()
        for perm in permissions:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    db.commit()
    db.refresh(role)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="users", entity="Role", entity_id=role.id, action="edit")
    return _role_detail_out(db, role)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("users", "users", "delete")),
):
    role = db.get(Role, role_id)
    if role is None or role.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="System roles from the workbook can't be deleted.")
    in_use = db.execute(select(UserRole).where(UserRole.role_id == role.id)).scalar_one_or_none()
    if in_use is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reassign the users on this role before deleting it.")

    for rp in db.execute(select(RolePermission).where(RolePermission.role_id == role.id)).scalars():
        db.delete(rp)
    db.delete(role)
    db.commit()
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="users", entity="Role", entity_id=role_id, action="delete")
    return None
