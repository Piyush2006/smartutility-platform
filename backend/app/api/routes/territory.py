from fastapi import APIRouter

from app.api.crud_factory import make_tenant_crud_router
from app.models.territory import Area, City, Country, Division, Premise, Region, State, SubArea, Zone
from app.schemas import territory as schemas

router = APIRouter(tags=["territory"])

_LEVELS = [
    (Region, schemas.RegionCreate, schemas.RegionUpdate, schemas.RegionOut, "/regions", "Region"),
    (Country, schemas.CountryCreate, schemas.CountryUpdate, schemas.CountryOut, "/countries", "Country"),
    (State, schemas.StateCreate, schemas.StateUpdate, schemas.StateOut, "/states", "State"),
    (City, schemas.CityCreate, schemas.CityUpdate, schemas.CityOut, "/cities", "City"),
    (Zone, schemas.ZoneCreate, schemas.ZoneUpdate, schemas.ZoneOut, "/zones", "Zone"),
    (Division, schemas.DivisionCreate, schemas.DivisionUpdate, schemas.DivisionOut, "/divisions", "Division"),
    (Area, schemas.AreaCreate, schemas.AreaUpdate, schemas.AreaOut, "/areas", "Area"),
    (SubArea, schemas.SubAreaCreate, schemas.SubAreaUpdate, schemas.SubAreaOut, "/sub-areas", "Sub-Area"),
    (Premise, schemas.PremiseCreate, schemas.PremiseUpdate, schemas.PremiseOut, "/premises", "Premise"),
]

for model, create_s, update_s, out_s, prefix, name in _LEVELS:
    router.include_router(
        make_tenant_crud_router(
            model=model,
            create_schema=create_s,
            update_schema=update_s,
            out_schema=out_s,
            prefix=prefix,
            tags=["territory"],
            module="territory",
            resource="territory",
            entity_name=name,
        )
    )
