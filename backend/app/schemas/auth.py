from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RoleOut(BaseModel):
    id: str
    name: str


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    tenant_id: Optional[str]
    is_superadmin: bool
    roles: list[RoleOut]
    # Distinct permission modules granted across all of the user's roles --
    # lets the frontend build its nav from real RBAC instead of a
    # hard-coded role->page map (CLAUDE.md: "never hard-code permissions
    # into UI components"). SuperAdmin bypasses all checks server-side, so
    # this is always [] for them; the frontend routes them separately.
    permission_modules: list[str] = []

    model_config = {"from_attributes": True}
