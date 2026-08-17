"""
Password hashing and JWT access/refresh token creation & verification.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(claims: dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
    to_encode = claims.copy()
    now = datetime.now(timezone.utc)
    to_encode.update({"exp": now + expires_delta, "iat": now, "type": token_type})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(*, user_id: str, tenant_id: Optional[str], role_ids: list[str]) -> str:
    claims = {"sub": user_id, "tenant_id": tenant_id, "role_ids": role_ids}
    return _create_token(claims, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(*, user_id: str) -> str:
    claims = {"sub": user_id}
    return _create_token(claims, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


def create_invite_token(*, user_id: str) -> str:
    """Single-purpose token emailed to a newly invited user so they can set
    their own password -- never used for API auth (see decode_token's
    'type' check, which rejects anything but 'access')."""
    claims = {"sub": user_id}
    return _create_token(claims, timedelta(days=settings.INVITE_TOKEN_EXPIRE_DAYS), "invite")


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
