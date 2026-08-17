import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.account import BILLING_FREQUENCIES, RATE_TYPES, VARIABLE_BASES


class CategoryCreate(BaseModel):
    name: str = Field(..., max_length=50, min_length=1)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, min_length=1)


class CategoryOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    model_config = {"from_attributes": True}


class SubCategoryCreate(BaseModel):
    category_id: str
    name: str = Field(..., max_length=50, min_length=1)


class SubCategoryUpdate(BaseModel):
    category_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=50, min_length=1)


class SubCategoryOut(BaseModel):
    id: str
    tenant_id: str
    category_id: str
    name: str
    model_config = {"from_attributes": True}


# ---- Rate --------------------------------------------------------------

class RateTierIn(BaseModel):
    tier_from: float = Field(..., ge=0)
    tier_to: Optional[float] = Field(None, gt=0)  # None = open-ended ("30+")
    price: float = Field(..., ge=0)


class TouRateIn(BaseModel):
    start_time: datetime.time
    end_time: datetime.time
    price: float = Field(..., ge=0)


class RateCreate(BaseModel):
    name: str = Field(..., max_length=50, min_length=1)
    rate_type: str
    rate: Optional[float] = Field(None, ge=0)
    basis: Optional[str] = None
    tiers: Optional[list[RateTierIn]] = None
    tou_rates: Optional[list[TouRateIn]] = None

    @model_validator(mode="after")
    def _validate_shape(self):
        if self.rate_type not in RATE_TYPES:
            raise ValueError(f"rate_type must be one of {RATE_TYPES}")
        if self.rate_type in ("fixed", "per_unit_area"):
            if self.rate is None:
                raise ValueError("rate is required for fixed / per_unit_area rate types")
        if self.rate_type == "variable":
            if self.basis not in VARIABLE_BASES:
                raise ValueError(f"basis must be one of {VARIABLE_BASES} for variable rates")
            if self.basis == "tiered" and not self.tiers:
                raise ValueError("tiers is required when basis=tiered")
            if self.basis == "time_of_use" and not self.tou_rates:
                raise ValueError("tou_rates is required when basis=time_of_use")
        return self


class RateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, min_length=1)
    rate: Optional[float] = Field(None, ge=0)


class RateTierOut(BaseModel):
    id: str
    tier_from: float
    tier_to: Optional[float]
    price: float
    model_config = {"from_attributes": True}


class TouRateOut(BaseModel):
    id: str
    start_time: datetime.time
    end_time: datetime.time
    price: float
    model_config = {"from_attributes": True}


class RateOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    rate_type: str
    rate: Optional[float]
    basis: Optional[str]
    tiers: list[RateTierOut] = []
    tou_rates: list[TouRateOut] = []
    model_config = {"from_attributes": True}


# ---- Plan ----------------------------------------------------------------

class PlanComponentIn(BaseModel):
    utility_service_id: str
    rate_id: str


class PlanCreate(BaseModel):
    name: str = Field(..., max_length=100, min_length=1)
    category_id: str
    sub_category_id: str
    tax_percent: Optional[float] = Field(None, ge=0, le=100)
    billing_frequency: Optional[str] = None
    components: list[PlanComponentIn] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _validate(self):
        if self.billing_frequency and self.billing_frequency not in BILLING_FREQUENCIES:
            raise ValueError(f"billing_frequency must be one of {BILLING_FREQUENCIES}")
        return self


class PlanUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, min_length=1)
    tax_percent: Optional[float] = Field(None, ge=0, le=100)
    billing_frequency: Optional[str] = None
    is_active: Optional[bool] = None


class PlanComponentOut(BaseModel):
    id: str
    utility_service_id: str
    rate_id: str
    model_config = {"from_attributes": True}


class PlanOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    category_id: str
    sub_category_id: str
    tax_percent: Optional[float]
    billing_frequency: Optional[str]
    is_active: bool
    components: list[PlanComponentOut] = []
    model_config = {"from_attributes": True}


# ---- Service Charge --------------------------------------------------------

class ServiceChargeCreate(BaseModel):
    name: str = Field(..., max_length=100, min_length=1)
    utility_service_id: Optional[str] = None  # None = "All"
    charge_type: str  # "fixed" | "variable"
    rate: float = Field(..., ge=0)
    plan_id: Optional[str] = None

    @model_validator(mode="after")
    def _validate(self):
        if self.charge_type not in ("fixed", "variable"):
            raise ValueError("charge_type must be 'fixed' or 'variable'")
        return self


class ServiceChargeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, min_length=1)
    rate: Optional[float] = Field(None, ge=0)


class ServiceChargeOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    utility_service_id: Optional[str]
    charge_type: str
    rate: float
    plan_id: Optional[str]
    model_config = {"from_attributes": True}
