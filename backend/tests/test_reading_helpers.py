import datetime
import uuid

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.consumer import Consumer
from app.models.meter import Meter
from app.models.reading import MeterReading
from app.models.service import UtilityService
from app.models.tenant import Tenant
from app.models.user import User
from app.services.reading_helpers import get_previous_reading


def test_falls_back_to_consumer_first_reading_when_no_prior_reading_row():
    """Regression: without this fallback, a meter's first-ever ingested
    reading has previous_reading=None -> treated as 0 -> VEE/billing see
    the full cumulative meter value as 'consumption' instead of the
    actual delta, spuriously failing every threshold rule."""
    db = SessionLocal()
    try:
        tenant = Tenant(name="Reading Helper Test Utility", status="active")
        db.add(tenant); db.flush()

        svc = db.query(UtilityService).filter_by(name="Water").first()
        if svc is None:
            svc = UtilityService(name="Water")
            db.add(svc); db.flush()

        unique = uuid.uuid4().hex[:8]
        meter = Meter(tenant_id=tenant.id, meter_no="M-RH", device_no=f"DEV-RH-{unique}", utility_service_id=svc.id, read_type="Manual", premise_id="premise-stub")
        db.add(meter); db.flush()

        user = User(tenant_id=tenant.id, email=f"rh-{unique}@demo.dev", full_name="Reading Helper Consumer", password_hash=hash_password("x"))
        db.add(user); db.flush()

        consumer = Consumer(
            tenant_id=tenant.id, full_name="Reading Helper Consumer", contact_no="+14155550111", email_address=f"rh-{unique}@demo.dev",
            ssn="123-45-6789", id_document_url="/uploads/x.pdf", premise_id="premise-stub", service_address="1 Test St",
            billing_address="1 Test St", plan_id="plan-stub", activation_date=datetime.date.today(), meter_id=meter.id,
            first_meter_reading=1000.0, first_meter_reading_date=datetime.date(2026, 1, 1), user_id=user.id,
        )
        db.add(consumer); db.commit()

        # No MeterReading rows exist yet -> must fall back to the consumer's baseline.
        prev_reading, prev_date = get_previous_reading(db, meter.id)
        assert prev_reading == 1000.0
        assert prev_date == datetime.date(2026, 1, 1)

        # Once a real reading exists, it takes priority over the consumer baseline.
        db.add(MeterReading(
            tenant_id=tenant.id, meter_id=meter.id, previous_reading=1000.0, previous_reading_date=datetime.date(2026, 1, 1),
            current_reading=1040.0, current_reading_date=datetime.date(2026, 2, 1), source="manual", status="Completed",
        ))
        db.commit()

        prev_reading2, prev_date2 = get_previous_reading(db, meter.id)
        assert prev_reading2 == 1040.0
        assert prev_date2 == datetime.date(2026, 2, 1)
    finally:
        db.close()


def test_no_baseline_when_meter_has_no_consumer():
    db = SessionLocal()
    try:
        tenant = Tenant(name="Reading Helper Test Utility 2", status="active")
        db.add(tenant); db.flush()
        svc = db.query(UtilityService).filter_by(name="Water").first()
        unique = uuid.uuid4().hex[:8]
        meter = Meter(tenant_id=tenant.id, meter_no="M-RH2", device_no=f"DEV-RH2-{unique}", utility_service_id=svc.id, read_type="Manual", premise_id="premise-stub")
        db.add(meter); db.commit()

        prev_reading, prev_date = get_previous_reading(db, meter.id)
        assert prev_reading is None
        assert prev_date is None
    finally:
        db.close()
