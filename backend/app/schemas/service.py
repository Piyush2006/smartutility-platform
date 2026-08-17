from pydantic import BaseModel


class UtilityServiceOut(BaseModel):
    id: str
    name: str
    model_config = {"from_attributes": True}


class TenantServiceOut(BaseModel):
    utility_service_id: str
    name: str
    is_enabled: bool


class TenantServiceToggle(BaseModel):
    utility_service_id: str
    is_enabled: bool
