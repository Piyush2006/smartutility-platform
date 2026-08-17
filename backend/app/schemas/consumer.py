import datetime
import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")
SSN_RE = re.compile(r"^\d{3}-\d{2}-\d{4}$")
NAME_RE = re.compile(r"^[A-Za-z ]+$")


class ConsumerCreate(BaseModel):
    """Workbook §11, exact field names. `id_document_url` is populated by
    a prior call to POST /consumers/id-document (multipart upload)."""

    full_name: str = Field(..., max_length=100, min_length=1)
    contact_no: str
    email_address: EmailStr
    ssn: str
    id_document_url: str
    premise_id: str
    service_address: str = Field(..., max_length=250, min_length=1)
    billing_address: str = Field(..., max_length=250, min_length=1)
    plan_id: str
    activation_date: datetime.date
    meter_id: str
    first_meter_reading: float = Field(..., ge=0)
    first_meter_reading_date: datetime.date

    @field_validator("full_name")
    @classmethod
    def _validate_name(cls, v):
        if not NAME_RE.match(v):
            raise ValueError("Enter full name.")
        return v

    @field_validator("contact_no")
    @classmethod
    def _validate_contact(cls, v):
        if not E164_RE.match(v):
            raise ValueError("Enter valid contact number.")
        return v

    @field_validator("ssn")
    @classmethod
    def _validate_ssn(cls, v):
        if not SSN_RE.match(v):
            raise ValueError("Enter valid SSN.")
        return v

    @field_validator("activation_date")
    @classmethod
    def _validate_activation(cls, v):
        if v < datetime.date.today():
            raise ValueError("Select a valid activation date.")
        return v

    @field_validator("first_meter_reading_date")
    @classmethod
    def _validate_first_reading_date(cls, v):
        if v > datetime.date.today():
            raise ValueError("Enter a valid meter reading date.")
        return v


class ConsumerUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    contact_no: Optional[str] = None
    email_address: Optional[EmailStr] = None
    service_address: Optional[str] = Field(None, max_length=250)
    billing_address: Optional[str] = Field(None, max_length=250)
    plan_id: Optional[str] = None
    status: Optional[str] = None
    property_manager_user_id: Optional[str] = None


class ConsumerOut(BaseModel):
    id: str
    tenant_id: str
    full_name: str
    contact_no: str
    email_address: str
    premise_id: str
    service_address: str
    billing_address: str
    plan_id: str
    activation_date: datetime.date
    meter_id: str
    first_meter_reading: float
    first_meter_reading_date: datetime.date
    status: str
    property_manager_user_id: Optional[str] = None
    model_config = {"from_attributes": True}
