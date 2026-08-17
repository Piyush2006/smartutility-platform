"""Shared helper for resolving a meter's "previous reading" baseline --
used by both the reading ingestion routes and demo/seed data so the two
never drift out of sync."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.consumer import Consumer
from app.models.reading import MeterReading


def get_previous_reading(db: Session, meter_id: str) -> tuple:
    """Previous (reading, date) for a meter: the latest MeterReading row if
    one exists, otherwise the consumer's First Meter Reading (workbook
    §11). Without this fallback, a meter's very first ingested reading has
    no baseline and consumption gets computed against zero -- i.e. the
    full cumulative meter value, not the actual delta -- which spuriously
    fails every VEE threshold rule."""
    row = db.execute(
        select(MeterReading).where(MeterReading.meter_id == meter_id).order_by(MeterReading.current_reading_date.desc())
    ).scalars().first()
    if row is not None:
        return row.current_reading, row.current_reading_date

    consumer = db.execute(select(Consumer).where(Consumer.meter_id == meter_id)).scalar_one_or_none()
    if consumer is not None:
        return consumer.first_meter_reading, consumer.first_meter_reading_date

    return None, None
