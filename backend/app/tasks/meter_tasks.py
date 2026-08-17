import datetime

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.meter import MeterRun, MeterSchedule
from app.services.meter_run_engine import generate_meter_run
from app.tasks.celery_app import celery_app

FREQUENCY_DAYS = {"Daily": 1, "Weekly": 7, "Monthly": 30, "Quarterly": 90}


def _is_due(schedule: MeterSchedule, today: datetime.date) -> bool:
    if not schedule.is_active or schedule.start_date > today:
        return False
    if not schedule.recurring:
        return schedule.last_run_at is None
    if schedule.last_run_at is None:
        return True
    days = FREQUENCY_DAYS.get(schedule.frequency, 30)
    return (today - schedule.last_run_at.date()).days >= days


@celery_app.task(name="app.tasks.meter_tasks.run_due_meter_schedules")
def run_due_meter_schedules() -> int:
    """Idempotent: only generates a run if the schedule hasn't already
    produced one today, so a beat re-fire never double-books a run."""
    db = SessionLocal()
    generated = 0
    try:
        today = datetime.date.today()
        for schedule in db.execute(select(MeterSchedule).where(MeterSchedule.is_active.is_(True))).scalars():
            if not _is_due(schedule, today):
                continue
            already_today = db.execute(
                select(MeterRun).where(MeterRun.meter_schedule_id == schedule.id, MeterRun.run_date == today)
            ).scalar_one_or_none()
            if already_today is not None:
                continue
            generate_meter_run(db, schedule)
            generated += 1
        return generated
    finally:
        db.close()
