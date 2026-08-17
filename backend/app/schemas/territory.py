from typing import Optional

from pydantic import BaseModel, Field


def _out_config():
    return {"from_attributes": True}


class RegionCreate(BaseModel):
    name: str = Field(..., max_length=50, min_length=1)


class RegionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, min_length=1)


class RegionOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    model_config = _out_config()


class CountryCreate(BaseModel):
    region_id: str
    name: str = Field(..., max_length=50, min_length=1)


class CountryUpdate(BaseModel):
    region_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=50, min_length=1)


class CountryOut(BaseModel):
    id: str
    tenant_id: str
    region_id: str
    name: str
    model_config = _out_config()


class StateCreate(BaseModel):
    country_id: str
    name: str = Field(..., max_length=50, min_length=1)


class StateUpdate(BaseModel):
    country_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=50, min_length=1)


class StateOut(BaseModel):
    id: str
    tenant_id: str
    country_id: str
    name: str
    model_config = _out_config()


class CityCreate(BaseModel):
    state_id: str
    name: str = Field(..., max_length=50, min_length=1)


class CityUpdate(BaseModel):
    state_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=50, min_length=1)


class CityOut(BaseModel):
    id: str
    tenant_id: str
    state_id: str
    name: str
    model_config = _out_config()


class ZoneCreate(BaseModel):
    city_id: str
    name: str = Field(..., max_length=50, min_length=1)


class ZoneUpdate(BaseModel):
    city_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=50, min_length=1)


class ZoneOut(BaseModel):
    id: str
    tenant_id: str
    city_id: str
    name: str
    model_config = _out_config()


class DivisionCreate(BaseModel):
    zone_id: str
    name: str = Field(..., max_length=50, min_length=1)


class DivisionUpdate(BaseModel):
    zone_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=50, min_length=1)


class DivisionOut(BaseModel):
    id: str
    tenant_id: str
    zone_id: str
    name: str
    model_config = _out_config()


class AreaCreate(BaseModel):
    division_id: str
    name: str = Field(..., max_length=50, min_length=1)


class AreaUpdate(BaseModel):
    division_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=50, min_length=1)


class AreaOut(BaseModel):
    id: str
    tenant_id: str
    division_id: str
    name: str
    model_config = _out_config()


class SubAreaCreate(BaseModel):
    area_id: str
    name: str = Field(..., max_length=50, min_length=1)
    servicable: bool = True


class SubAreaUpdate(BaseModel):
    area_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=50, min_length=1)
    servicable: Optional[bool] = None


class SubAreaOut(BaseModel):
    id: str
    tenant_id: str
    area_id: str
    name: str
    servicable: bool
    model_config = _out_config()


class PremiseCreate(BaseModel):
    sub_area_id: str
    name: str = Field(..., max_length=50, min_length=1)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class PremiseUpdate(BaseModel):
    sub_area_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=50, min_length=1)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class PremiseOut(BaseModel):
    id: str
    tenant_id: str
    sub_area_id: str
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    model_config = _out_config()
