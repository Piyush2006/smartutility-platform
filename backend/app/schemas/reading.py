import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class MeterReadingCreate(BaseModel):
    meter_id: str
    meter_run_id: Optional[str] = None
    current_reading: float = Field(..., ge=0)
    current_reading_date: datetime.date

    @model_validator(mode="after")
    def _validate(self):
        if self.current_reading_date > datetime.date.today():
            raise ValueError("Enter a valid current reading date.")
        return self


class MeterReadingOut(BaseModel):
    id: str
    tenant_id: str
    meter_id: str
    meter_run_id: Optional[str]
    read_cycle_id: Optional[str]
    previous_reading: Optional[float]
    previous_reading_date: Optional[datetime.date]
    current_reading: float
    current_reading_date: datetime.date
    source: str
    status: str
    is_duplicate: bool
    model_config = {"from_attributes": True}


class ReadingHistoryOut(BaseModel):
    read_cycle: Optional[str]
    meter_no: str
    device_no: str
    previous_reading: Optional[float]
    previous_reading_date: Optional[datetime.date]
    current_reading: float
    current_reading_date: datetime.date
    status: str


class RevisitResolve(BaseModel):
    corrected_current_reading: Optional[float] = Field(None, ge=0)


class ImportSummaryOut(BaseModel):
    id: str
    file_name: str
    file_url: str
    total_rows: int
    valid_rows: int
    invalid_rows: int


class ValidationBreakdownOut(BaseModel):
    read_cycle_id: str
    read_cycle_name: str
    schedule_start_date: Optional[datetime.date]
    schedule_end_date: Optional[datetime.date]
    total_meters: int
    readings: int
    pending: int
    v1: int
    v2: int
    revisit: int
    completed: int
