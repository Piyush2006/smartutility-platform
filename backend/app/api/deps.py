"""
Auth, RBAC and tenant-isolation dependencies.

Rule (CLAUDE.md #16/#17): tenant isolation is enforced HERE, server-side,
on every request -- never trust a tenant_id supplied by the frontend.
"""
from typing import Optional
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)


@dataclass
class CurrentUser:
    id: str
    tenant_id: Optional[str]
    is_superadmin: bool
    role_ids: list[str]
    user: User


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> CurrentUser:
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return CurrentUser(
        id=user.id,
        tenant_id=payload.get("tenant_id"),
        is_superadmin=user.is_superadmin,
        role_ids=payload.get("role_ids", []),
        user=user,
    )


def get_tenant_id(current_user: CurrentUser = Depends(get_current_user)) -> str:
    """
    Server-side tenant scope for every tenant-owned query.
    SuperAdmin has no tenant_id -- routes that need a concrete tenant must
    require SuperAdmin to pass one explicitly (see require_superadmin) rather
    than falling back to this dependency.
    """
    if current_user.tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant context for this user")
    return current_user.tenant_id


def require_superadmin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not current_user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SuperAdmin access required")
    return current_user


def require_permission(module: str, resource: str, action: str):
    """
    module -> resource -> action check (CLAUDE.md #4). SuperAdmin bypasses
    (platform-wide access). Never hard-code permission checks into UI --
    the frontend only reads /auth/me roles/permissions to decide what to show.
    """

    def _checker(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> CurrentUser:
        if current_user.is_superadmin:
            return current_user
        if not current_user.role_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        stmt = (
            select(Permission.id)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(
                RolePermission.role_id.in_(current_user.role_ids),
                Permission.module == module,
                Permission.resource == resource,
                Permission.action == action,
            )
        )
        allowed = db.execute(stmt).first() is not None
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return _checker


def get_user_role_ids(db: Session, user_id: str) -> list[str]:
    stmt = select(UserRole.role_id).where(UserRole.user_id == user_id)
    return [row[0] for row in db.execute(stmt).all()]


def get_user_roles_with_names(db: Session, user_id: str) -> list[Role]:
    stmt = select(Role).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
    return list(db.execute(stmt).scalars().all())
