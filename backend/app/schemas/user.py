from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RoleSummaryOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_system: bool = False
    model_config = {"from_attributes": True}


class TenantUserCreate(BaseModel):
    """Invite a staff user into the current tenant -- creates the login
    (locked with an unrevealed random password) and emails them a link to
    set their own password (see app/services/email_service.py). The
    account can't be logged into until they do."""

    full_name: str = Field(..., max_length=100, min_length=1)
    email: EmailStr
    role_id: str


class TenantUserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100, min_length=1)
    is_active: Optional[bool] = None
    role_id: Optional[str] = None  # replaces the user's role assignment(s) with this single role


class TenantUserOut(BaseModel):
    id: str
    full_name: str
    email: str
    is_active: bool
    roles: list[RoleSummaryOut] = []


class UserInviteOut(BaseModel):
    user: TenantUserOut
    email_sent: bool
    invite_link: str  # always included -- lets the admin share it manually if email_sent is False (no SMTP configured)


class PermissionSummaryOut(BaseModel):
    id: str
    module: str
    resource: str
    action: str
    description: Optional[str] = None
    model_config = {"from_attributes": True}


class RoleDetailOut(RoleSummaryOut):
    permissions: list[PermissionSummaryOut] = []


class RoleCreate(BaseModel):
    name: str = Field(..., max_length=50, min_length=1)
    description: Optional[str] = Field(None, max_length=255)
    permission_ids: list[str] = Field(..., min_length=1)


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, min_length=1)
    description: Optional[str] = Field(None, max_length=255)
    permission_ids: Optional[list[str]] = Field(None, min_length=1)  # replaces the full permission set when provided
