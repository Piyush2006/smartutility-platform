"""
VEE Schedules (workbook §16) define a repetition interval for re-running
validation over the window [start_date, end_date]. Actual rule evaluation
already happens synchronously on every reading ingest (app/services/
vee_engine.py, called from app/api/routes/reading.py) -- this task exists
for the case where the workbook expects VEE to also sweep periodically
(e.g. to catch readings a rule config change should now flag).
"""
import datetime

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.reading import MeterReading
from app.models.vee import VeeSchedule
from app.services.vee_engine import evaluate_reading
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.vee_tasks.run_due_vee_schedules")
def run_due_vee_schedules() -> int:
    db = SessionLocal()
    swept = 0
    try:
        today = datetime.date.today()
        active_schedules = db.execute(
            select(VeeSchedule).where(VeeSchedule.is_active.is_(True), VeeSchedule.start_date <= today, VeeSchedule.end_date >= today)
        ).scalars().all()
        if not active_schedules:
            return 0
        # Re-sweep any reading still awaiting a stage transition -- idempotent:
        # evaluate_reading is a no-op for readings already Completed.
        pending = db.execute(select(MeterReading).where(MeterReading.status.in_(["Received", "V2"]))).scalars()
        for reading in pending:
            evaluate_reading(db, reading)
            swept += 1
        return swept
    finally:
        db.close()
