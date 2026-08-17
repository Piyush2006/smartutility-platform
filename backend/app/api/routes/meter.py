import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_tenant_id, require_permission
from app.core.database import get_db
from app.models.meter import (
    Meter,
    MeterRun,
    MeterSchedule,
    ReadCycle,
    ReadCycleUtilityService,
    Route,
    RouteMeter,
    RouteUtilityService,
)
from app.models.territory import Premise
from app.schemas import meter as schemas
from app.services.audit import record_audit
from app.services.meter_run_engine import generate_meter_run

router = APIRouter(tags=["meter"])


# ---- Meters -----------------------------------------------------------

@router.get("/meters", response_model=list[schemas.MeterOut])
def list_meters(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("meter", "meter", "view"))):
    return list(db.execute(select(Meter).where(Meter.tenant_id == tenant_id)).scalars())


@router.get("/meters/available", response_model=list[schemas.MeterOut])
def list_available_meters(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("meter", "meter", "view"))):
    """Unassigned meters -- what the Consumer creation form's Meter dropdown offers."""
    return list(db.execute(select(Meter).where(Meter.tenant_id == tenant_id, Meter.is_assigned.is_(False))).scalars())


@router.post("/meters", response_model=schemas.MeterOut, status_code=status.HTTP_201_CREATED)
def create_meter(
    payload: schemas.MeterCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("meter", "meter", "create")),
):
    premise = db.get(Premise, payload.premise_id)
    if premise is None or premise.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select a premise.")
    dup = db.execute(select(Meter).where(Meter.tenant_id == tenant_id, Meter.device_no == payload.device_no)).scalar_one_or_none()
    if dup is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter a valid Device Number.")
    meter = Meter(tenant_id=tenant_id, **payload.model_dump())
    db.add(meter)
    db.commit()
    db.refresh(meter)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="meter", entity="Meter", entity_id=meter.id, action="create", new_value=payload.model_dump(mode="json"))
    return meter


@router.patch("/meters/{meter_id}", response_model=schemas.MeterOut)
def update_meter(
    meter_id: str, payload: schemas.MeterUpdate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("meter", "meter", "edit")),
):
    meter = db.get(Meter, meter_id)
    if meter is None or meter.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meter not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(meter, key, value)
    db.commit()
    db.refresh(meter)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="meter", entity="Meter", entity_id=meter.id, action="edit")
    return meter


# ---- Routes -------------------------------------------------------------

def _route_out(db: Session, route: Route) -> schemas.RouteOut:
    service_ids = [r[0] for r in db.execute(select(RouteUtilityService.utility_service_id).where(RouteUtilityService.route_id == route.id)).all()]
    meter_count = db.execute(select(func.count()).select_from(RouteMeter).where(RouteMeter.route_id == route.id)).scalar_one()
    return schemas.RouteOut(
        id=route.id, tenant_id=route.tenant_id, name=route.name, read_type=route.read_type,
        premise_id=route.premise_id, utility_service_ids=service_ids, meter_count=meter_count,
    )


@router.get("/routes", response_model=list[schemas.RouteOut])
def list_routes(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("meter", "meter", "view"))):
    routes = list(db.execute(select(Route).where(Route.tenant_id == tenant_id)).scalars())
    return [_route_out(db, r) for r in routes]


@router.post("/routes", response_model=schemas.RouteOut, status_code=status.HTTP_201_CREATED)
def create_route(
    payload: schemas.RouteCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("meter", "meter", "create")),
):
    route = Route(tenant_id=tenant_id, name=payload.name, read_type=payload.read_type, premise_id=payload.premise_id)
    db.add(route)
    db.flush()
    for svc_id in payload.utility_service_ids:
        db.add(RouteUtilityService(route_id=route.id, utility_service_id=svc_id))
    # Auto-assign every meter at this premise matching one of the route's services.
    meters = db.execute(
        select(Meter).where(Meter.tenant_id == tenant_id, Meter.premise_id == payload.premise_id, Meter.utility_service_id.in_(payload.utility_service_ids))
    ).scalars()
    for meter in meters:
        db.add(RouteMeter(route_id=route.id, meter_id=meter.id))
    db.commit()
    db.refresh(route)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="meter", entity="Route", entity_id=route.id, action="create", new_value=payload.model_dump(mode="json"))
    return _route_out(db, route)


@router.get("/routes/{route_id}", response_model=schemas.RouteOut)
def get_route(route_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("meter", "meter", "view"))):
    route = db.get(Route, route_id)
    if route is None or route.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    return _route_out(db, route)


@router.patch("/routes/{route_id}", response_model=schemas.RouteOut)
def update_route(
    route_id: str, payload: schemas.RouteUpdate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("meter", "meter", "edit")),
):
    """Only name/read_type can be edited -- changing premise or services
    would invalidate the auto-assigned meters, so that requires recreating
    the route."""
    route = db.get(Route, route_id)
    if route is None or route.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(route, key, value)
    db.commit()
    db.refresh(route)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="meter", entity="Route", entity_id=route.id, action="edit")
    return _route_out(db, route)


# ---- Read Cycles ----------------------------------------------------------

def _read_cycle_out(db: Session, rc: ReadCycle) -> schemas.ReadCycleOut:
    service_ids = [r[0] for r in db.execute(select(ReadCycleUtilityService.utility_service_id).where(ReadCycleUtilityService.read_cycle_id == rc.id)).all()]
    meter_count = db.execute(select(func.count()).select_from(RouteMeter).where(RouteMeter.route_id == rc.route_id)).scalar_one()
    return schemas.ReadCycleOut(
        id=rc.id, tenant_id=rc.tenant_id, name=rc.name, read_type=rc.read_type, route_id=rc.route_id,
        utility_service_ids=service_ids, meter_count=meter_count,
    )


@router.get("/read-cycles", response_model=list[schemas.ReadCycleOut])
def list_read_cycles(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("meter", "meter", "view"))):
    cycles = list(db.execute(select(ReadCycle).where(ReadCycle.tenant_id == tenant_id)).scalars())
    return [_read_cycle_out(db, c) for c in cycles]


@router.post("/read-cycles", response_model=schemas.ReadCycleOut, status_code=status.HTTP_201_CREATED)
def create_read_cycle(
    payload: schemas.ReadCycleCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("meter", "meter", "create")),
):
    route = db.get(Route, payload.route_id)
    if route is None or route.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select a route.")
    rc = ReadCycle(tenant_id=tenant_id, name=payload.name, read_type=payload.read_type, route_id=payload.route_id)
    db.add(rc)
    db.flush()
    for svc_id in payload.utility_service_ids:
        db.add(ReadCycleUtilityService(read_cycle_id=rc.id, utility_service_id=svc_id))
    db.commit()
    db.refresh(rc)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="meter", entity="ReadCycle", entity_id=rc.id, action="create", new_value=payload.model_dump(mode="json"))
    return _read_cycle_out(db, rc)


@router.get("/read-cycles/{read_cycle_id}", response_model=schemas.ReadCycleOut)
def get_read_cycle(read_cycle_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("meter", "meter", "view"))):
    rc = db.get(ReadCycle, read_cycle_id)
    if rc is None or rc.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Read cycle not found")
    return _read_cycle_out(db, rc)


@router.patch("/read-cycles/{read_cycle_id}", response_model=schemas.ReadCycleOut)
def update_read_cycle(
    read_cycle_id: str, payload: schemas.ReadCycleUpdate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("meter", "meter", "edit")),
):
    rc = db.get(ReadCycle, read_cycle_id)
    if rc is None or rc.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Read cycle not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rc, key, value)
    db.commit()
    db.refresh(rc)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="meter", entity="ReadCycle", entity_id=rc.id, action="edit")
    return _read_cycle_out(db, rc)


# ---- Meter Schedules + Runs -----------------------------------------------

@router.get("/meter-schedules", response_model=list[schemas.MeterScheduleOut])
def list_meter_schedules(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("meter", "meter", "view"))):
    return list(db.execute(select(MeterSchedule).where(MeterSchedule.tenant_id == tenant_id)).scalars())


@router.post("/meter-schedules", response_model=schemas.MeterScheduleOut, status_code=status.HTTP_201_CREATED)
def create_meter_schedule(
    payload: schemas.MeterScheduleCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("meter", "meter", "create")),
):
    rc = db.get(ReadCycle, payload.read_cycle_id)
    if rc is None or rc.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select a cycle.")
    schedule = MeterSchedule(tenant_id=tenant_id, **payload.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="meter", entity="MeterSchedule", entity_id=schedule.id, action="create", new_value=payload.model_dump(mode="json"))
    return schedule


@router.get("/meter-schedules/{schedule_id}", response_model=schemas.MeterScheduleOut)
def get_meter_schedule(schedule_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("meter", "meter", "view"))):
    schedule = db.get(MeterSchedule, schedule_id)
    if schedule is None or schedule.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return schedule


@router.patch("/meter-schedules/{schedule_id}", response_model=schemas.MeterScheduleOut)
def update_meter_schedule(
    schedule_id: str, payload: schemas.MeterScheduleUpdate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("meter", "meter", "edit")),
):
    schedule = db.get(MeterSchedule, schedule_id)
    if schedule is None or schedule.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(schedule, key, value)
    db.commit()
    db.refresh(schedule)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="meter", entity="MeterSchedule", entity_id=schedule.id, action="edit")
    return schedule


@router.get("/meter-runs", response_model=list[schemas.MeterRunOut])
def list_meter_runs(tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db), _=Depends(require_permission("meter", "meter", "view"))):
    return list(db.execute(select(MeterRun).where(MeterRun.tenant_id == tenant_id)).scalars())


@router.post("/meter-schedules/{schedule_id}/generate-run", response_model=schemas.MeterRunOut, status_code=status.HTTP_201_CREATED)
def trigger_meter_run(
    schedule_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission("meter", "meter", "execute")),
):
    """Manual 'Generate Now' -- the same logic Celery Beat calls automatically
    for due recurring schedules in production (app/tasks/meter_tasks.py)."""
    schedule = db.get(MeterSchedule, schedule_id)
    if schedule is None or schedule.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    run = generate_meter_run(db, schedule)
    record_audit(db, tenant_id=tenant_id, user_id=current.id, module="meter", entity="MeterRun", entity_id=run.id, action="execute")
    return run
