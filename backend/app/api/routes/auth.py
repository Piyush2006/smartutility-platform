from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_user_role_ids, get_user_roles_with_names
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.models.rbac import Permission, RolePermission
from app.models.user import User
from app.schemas.auth import LoginRequest, MeResponse, RefreshRequest, RoleOut, SetPasswordRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    role_ids = get_user_role_ids(db, user.id)
    access = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role_ids=role_ids)
    refresh = create_refresh_token(user_id=user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token") from exc
    if claims.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user = db.get(User, claims.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return _issue_tokens(db, user)


@router.post("/set-password", response_model=TokenResponse)
def set_password(payload: SetPasswordRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Consumes an invite-token link (see app/services/email_service.py):
    sets the invited user's real password and logs them straight in."""
    try:
        claims = decode_token(payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invite link is invalid or has expired.") from exc
    if claims.get("type") != "invite":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invite link is invalid or has expired.")

    user = db.get(User, claims.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invite link is invalid or has expired.")

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return _issue_tokens(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> None:
    # Stateless JWT: logout is enforced client-side by discarding tokens.
    # Left as a real endpoint (rather than omitted) so the frontend has a
    # stable contract if/when server-side token revocation is added.
    return None


@router.get("/me", response_model=MeResponse)
def me(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> MeResponse:
    roles = get_user_roles_with_names(db, current_user.id)
    user = current_user.user

    modules: list[str] = []
    if not user.is_superadmin and current_user.role_ids:
        stmt = (
            select(Permission.module)
            .distinct()
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id.in_(current_user.role_ids))
        )
        modules = [row[0] for row in db.execute(stmt).all()]

    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=user.tenant_id,
        is_superadmin=user.is_superadmin,
        roles=[RoleOut(id=r.id, name=r.name) for r in roles],
        permission_modules=modules,
    )
