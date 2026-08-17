"""
Bill Run generation (workbook §19): "no create form -- Bill schedules
generate Bill Runs automatically." One run bills every consumer attached
to the schedule's Bill Cycle premises, using each consumer's latest
Completed meter reading.
"""
import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.billing import BillCyclePremise, BillRun, BillSchedule
from app.models.consumer import Consumer
from app.models.reading import MeterReading
from app.services.billing_engine import BillingError, generate_bill


def generate_bill_run(db: Session, schedule: BillSchedule) -> BillRun:
    premise_ids = [
        r[0] for r in db.execute(select(BillCyclePremise.premise_id).where(BillCyclePremise.bill_cycle_id == schedule.bill_cycle_id)).all()
    ]
    consumers = list(
        db.execute(select(Consumer).where(Consumer.tenant_id == schedule.tenant_id, Consumer.premise_id.in_(premise_ids))).scalars()
    ) if premise_ids else []

    run = BillRun(
        tenant_id=schedule.tenant_id, bill_schedule_id=schedule.id, bill_cycle_id=schedule.bill_cycle_id,
        bill_template_id=schedule.bill_template_id, consumer_count=len(consumers),
        bill_start_date=schedule.bill_start_date, bill_end_date=schedule.bill_end_date, status="generating",
    )
    db.add(run)
    db.flush()

    errors = []
    billed = 0
    for consumer in consumers:
        reading = db.execute(
            select(MeterReading)
            .where(MeterReading.meter_id == consumer.meter_id, MeterReading.status == "Completed")
            .order_by(MeterReading.current_reading_date.desc())
        ).scalars().first()
        if reading is None:
            errors.append(f"{consumer.full_name}: no completed meter reading available.")
            continue
        try:
            generate_bill(
                db, bill_run_id=run.id, consumer=consumer, reading=reading,
                service_period_start=schedule.bill_start_date, service_period_end=schedule.bill_end_date,
            )
            billed += 1
        except BillingError as exc:
            errors.append(f"{consumer.full_name}: {exc}")

    run.status = "completed" if not errors else ("completed" if billed else "failed")
    run.error_message = "; ".join(errors) if errors else None
    schedule.last_run_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(run)
    return run
