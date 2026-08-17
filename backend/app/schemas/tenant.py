import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")


class TenantCreate(BaseModel):
    """Utility onboarding (workbook §7). Creates the tenant + a Utility Admin
    login in one step -- see app/services/onboarding.py."""

    name: str = Field(..., max_length=50, min_length=1)
    phone_no: str
    address: str = Field(..., max_length=250, min_length=1)
    website: str
    email: EmailStr
    currency: str
    timezone: str
    date_format: str
    e_transfer: Optional[str] = None
    hst_gst_no: Optional[str] = None

    admin_full_name: str = Field(..., max_length=100, min_length=1)
    admin_email: EmailStr

    @field_validator("phone_no")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        if not E164_RE.match(v):
            raise ValueError("Enter a valid phone number with country code (E.164, e.g. +14155552671).")
        return v

    @field_validator("website")
    @classmethod
    def _validate_website(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Enter a valid website URL.")
        return v


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, min_length=1)
    phone_no: Optional[str] = None
    address: Optional[str] = Field(None, max_length=250)
    website: Optional[str] = None
    email: Optional[EmailStr] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    date_format: Optional[str] = None
    e_transfer: Optional[str] = None
    hst_gst_no: Optional[str] = None

    @field_validator("phone_no")
    @classmethod
    def _validate_phone(cls, v):
        if v is not None and not E164_RE.match(v):
            raise ValueError("Enter a valid phone number with country code (E.164, e.g. +14155552671).")
        return v

    @field_validator("website")
    @classmethod
    def _validate_website(cls, v):
        if v is not None and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Enter a valid website URL.")
        return v


class TenantStatusUpdate(BaseModel):
    status: str  # "active" | "suspended"

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        if v not in ("active", "suspended"):
            raise ValueError("status must be 'active' or 'suspended'")
        return v


class TenantOut(BaseModel):
    id: str
    name: str
    status: str
    logo_url: Optional[str] = None
    phone_no: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    date_format: Optional[str] = None
    e_transfer: Optional[str] = None
    hst_gst_no: Optional[str] = None

    model_config = {"from_attributes": True}
