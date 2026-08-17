"""
Meter Run generation (workbook §14): "no create form -- Schedules generate
Meter Runs automatically." Called both from the manual 'Generate Now' API
route and from the Celery Beat task for due recurring schedules.
"""
import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meter import Meter, MeterRun, MeterSchedule, ReadCycle, RouteMeter


def generate_meter_run(db: Session, schedule: MeterSchedule) -> MeterRun:
    read_cycle = db.get(ReadCycle, schedule.read_cycle_id)
    meter_ids = [
        r[0] for r in db.execute(select(RouteMeter.meter_id).where(RouteMeter.route_id == read_cycle.route_id)).all()
    ]
    premises = {m.premise_id for m in db.execute(select(Meter).where(Meter.id.in_(meter_ids))).scalars()} if meter_ids else set()

    run = MeterRun(
        tenant_id=schedule.tenant_id,
        meter_schedule_id=schedule.id,
        run_date=datetime.date.today(),
        premise_count=len(premises),
        meter_count=len(meter_ids),
        readings_received=0,
        status="pending",
    )
    db.add(run)
    schedule.last_run_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(run)
    return run
