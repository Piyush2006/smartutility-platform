import datetime
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.meter import READ_TYPES, ROUTE_READ_TYPES, SCHEDULE_FREQUENCIES

METER_NO_RE = re.compile(r"^[A-Za-z0-9\-]+$")


class MeterCreate(BaseModel):
    meter_no: str = Field(..., max_length=30, min_length=1)
    device_no: str = Field(..., max_length=30, min_length=1)
    utility_service_id: str
    read_type: str
    premise_id: str
    installation_date: Optional[datetime.date] = None
    latitude: Optional[float] = Field(None, ge=-180, le=180)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    unit: Optional[str] = Field(None, max_length=10)
    floor: Optional[str] = Field(None, max_length=10)
    meter_dial: Optional[float] = None

    @field_validator("meter_no")
    @classmethod
    def _validate_meter_no(cls, v):
        if not METER_NO_RE.match(v):
            raise ValueError("Enter a valid Meter Number (letters, numbers, hyphens only).")
        return v

    @field_validator("read_type")
    @classmethod
    def _validate_read_type(cls, v):
        if v not in READ_TYPES:
            raise ValueError(f"read_type must be one of {READ_TYPES}")
        return v

    @field_validator("installation_date")
    @classmethod
    def _validate_install_date(cls, v):
        if v is not None and v > datetime.date.today():
            raise ValueError("Installation date must be today or earlier.")
        return v


class MeterUpdate(BaseModel):
    meter_no: Optional[str] = Field(None, max_length=30)
    device_no: Optional[str] = Field(None, max_length=30)
    read_type: Optional[str] = None
    installation_date: Optional[datetime.date] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    unit: Optional[str] = Field(None, max_length=10)
    floor: Optional[str] = Field(None, max_length=10)


class MeterOut(BaseModel):
    id: str
    tenant_id: str
    meter_no: str
    device_no: str
    utility_service_id: str
    read_type: str
    premise_id: str
    installation_date: Optional[datetime.date]
    latitude: Optional[float]
    longitude: Optional[float]
    unit: Optional[str]
    floor: Optional[str]
    meter_dial: Optional[float]
    is_assigned: bool
    model_config = {"from_attributes": True}


class RouteCreate(BaseModel):
    name: str = Field(..., max_length=50, min_length=1)
    read_type: str
    premise_id: str
    utility_service_ids: list[str] = Field(..., min_length=1)

    @field_validator("read_type")
    @classmethod
    def _validate_read_type(cls, v):
        if v not in ROUTE_READ_TYPES:
            raise ValueError(f"read_type must be one of {ROUTE_READ_TYPES}")
        return v


class RouteUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    read_type: Optional[str] = None


class RouteOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    read_type: str
    premise_id: str
    utility_service_ids: list[str] = []
    meter_count: int = 0
    model_config = {"from_attributes": True}


class ReadCycleCreate(BaseModel):
    name: str = Field(..., max_length=50, min_length=1)
    read_type: str
    route_id: str
    utility_service_ids: list[str] = Field(..., min_length=1)


class ReadCycleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    read_type: Optional[str] = None


class ReadCycleOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    read_type: str
    route_id: str
    utility_service_ids: list[str] = []
    meter_count: int = 0
    model_config = {"from_attributes": True}


class MeterScheduleCreate(BaseModel):
    read_cycle_id: str
    recurring: bool = False
    frequency: Optional[str] = None
    start_date: datetime.date
    due_days: Optional[int] = Field(None, ge=1, le=60)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("start_date")
    @classmethod
    def _validate_start_date(cls, v):
        if v < datetime.date.today():
            raise ValueError("Start date is required and cannot be in the past.")
        return v

    @field_validator("frequency")
    @classmethod
    def _validate_frequency(cls, v):
        if v is not None and v not in SCHEDULE_FREQUENCIES:
            raise ValueError(f"frequency must be one of {SCHEDULE_FREQUENCIES}")
        return v


class MeterScheduleUpdate(BaseModel):
    is_active: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=500)


class MeterScheduleOut(BaseModel):
    id: str
    tenant_id: str
    read_cycle_id: str
    recurring: bool
    frequency: Optional[str]
    start_date: datetime.date
    due_days: Optional[int]
    description: Optional[str]
    is_active: bool
    model_config = {"from_attributes": True}


class MeterRunOut(BaseModel):
    id: str
    tenant_id: str
    meter_schedule_id: str
    run_date: datetime.date
    premise_count: int
    meter_count: int
    readings_received: int
    status: str
    model_config = {"from_attributes": True}
