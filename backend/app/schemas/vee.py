import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.vee import VEE_INTERVALS


class VeeRuleCreate(BaseModel):
    name: str = Field(..., max_length=50, min_length=1)
    utility_service_id: str
    read_type: str
    rule_type: str
    parameters: Optional[dict] = None
    description: Optional[str] = Field(None, max_length=500)


class VeeRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    parameters: Optional[dict] = None
    description: Optional[str] = Field(None, max_length=500)


class VeeRuleOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    utility_service_id: str
    read_type: str
    rule_type: str
    parameters: Optional[dict]
    description: Optional[str]
    model_config = {"from_attributes": True}


class VeeConfigCreate(BaseModel):
    name: str = Field(..., max_length=50, min_length=1)
    utility_service_id: str
    read_type: str
    rule_ids: list[str] = Field(..., min_length=1)


class VeeConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)


class VeeConfigOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    utility_service_id: str
    read_type: str
    rule_ids: list[str] = []
    model_config = {"from_attributes": True}


class VeeScheduleCreate(BaseModel):
    vee_config_id: str
    start_date: datetime.date
    repetition_interval: str
    end_date: datetime.date

    @model_validator(mode="after")
    def _validate(self):
        if self.repetition_interval not in VEE_INTERVALS:
            raise ValueError(f"repetition_interval must be one of {VEE_INTERVALS}")
        if self.end_date <= self.start_date:
            raise ValueError("End date must be after the start date.")
        return self


class VeeScheduleUpdate(BaseModel):
    is_active: Optional[bool] = None


class VeeScheduleOut(BaseModel):
    id: str
    tenant_id: str
    vee_config_id: str
    start_date: datetime.date
    repetition_interval: str
    end_date: datetime.date
    is_active: bool
    model_config = {"from_attributes": True}
