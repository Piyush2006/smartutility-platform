import datetime

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.billing import Bill, BillRun, BillSchedule
from app.services.bill_run_engine import generate_bill_run
from app.services.pdf_generator import generate_bill_pdf
from app.tasks.celery_app import celery_app


def _is_due(schedule: BillSchedule, now: datetime.datetime) -> bool:
    if not schedule.is_active:
        return False
    if schedule.last_run_at is not None:
        return False  # one-shot schedules never re-fire; recurring re-scheduling is out of scope for this MVP
    generation_dt = datetime.datetime.combine(schedule.bill_generation_date, schedule.bill_generation_time, tzinfo=datetime.timezone.utc)
    return now >= generation_dt


@celery_app.task(name="app.tasks.billing_tasks.run_due_bill_schedules")
def run_due_bill_schedules() -> int:
    """Idempotent: last_run_at gates re-execution, so a beat re-fire never
    double-bills a schedule."""
    db = SessionLocal()
    generated = 0
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        for schedule in db.execute(select(BillSchedule).where(BillSchedule.is_active.is_(True))).scalars():
            if not _is_due(schedule, now):
                continue
            run = generate_bill_run(db, schedule)
            for bill in db.execute(select(Bill).where(Bill.bill_run_id == run.id)).scalars():
                bill.pdf_url = generate_bill_pdf(db, bill)
            db.commit()
            generated += 1
        return generated
    finally:
        db.close()
