import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import pytest

from app.core.database import SessionLocal
from app.models.meter import Meter
from app.models.reading import MeterReading
from app.models.service import UtilityService
from app.models.tenant import Tenant
from app.models.vee import VeeConfig, VeeConfigRule, VeeRule
from app.services.vee_engine import _evaluate_no_reading, _evaluate_threshold_alert, evaluate_reading


@dataclass
class FakeReading:
    current_reading: float
    previous_reading: Optional[float]
    current_reading_date: datetime.date
    previous_reading_date: Optional[datetime.date]


def test_no_reading_passes_when_within_cadence():
    reading = FakeReading(120, 100, datetime.date(2026, 2, 1), datetime.date(2026, 1, 1))
    passed, _ = _evaluate_no_reading(reading, {"max_days_without_reading": 45})
    assert passed is True


def test_no_reading_fails_when_gap_too_large():
    reading = FakeReading(120, 100, datetime.date(2026, 3, 1), datetime.date(2026, 1, 1))
    passed, message = _evaluate_no_reading(reading, {"max_days_without_reading": 45})
    assert passed is False
    assert "59 days" in message


def test_no_reading_passes_on_first_ever_reading():
    reading = FakeReading(50, None, datetime.date(2026, 1, 1), None)
    passed, _ = _evaluate_no_reading(reading, {})
    assert passed is True


def test_threshold_alert_passes_within_bounds():
    reading = FakeReading(150, 100, datetime.date(2026, 1, 1), datetime.date(2025, 12, 1))
    passed, _ = _evaluate_threshold_alert(reading, {"min_units": 0, "max_units": 100})
    assert passed is True


def test_threshold_alert_fails_above_max():
    reading = FakeReading(500, 100, datetime.date(2026, 1, 1), datetime.date(2025, 12, 1))
    passed, message = _evaluate_threshold_alert(reading, {"min_units": 0, "max_units": 100})
    assert passed is False
    assert "above maximum" in message


def test_threshold_alert_fails_below_min():
    reading = FakeReading(100, 100, datetime.date(2026, 1, 1), datetime.date(2025, 12, 1))
    passed, message = _evaluate_threshold_alert(reading, {"min_units": 5, "max_units": 100})
    assert passed is False
    assert "below minimum" in message


@pytest.fixture
def failing_reading():
    """A reading that will fail the same Threshold Alert rule at both V1
    and V2 -- regression coverage for the bug where a reading that failed
    V1 got permanently stuck at status='V2' because evaluate_reading only
    advanced one stage per call."""
    db = SessionLocal()
    try:
        tenant = Tenant(name="VEE Test Utility", status="active")
        db.add(tenant)
        db.flush()

        svc = db.query(UtilityService).filter_by(name="Water").first()
        if svc is None:
            svc = UtilityService(name="Water")
            db.add(svc)
            db.flush()

        unique = uuid.uuid4().hex[:8]
        meter = Meter(tenant_id=tenant.id, meter_no="M-VEE", device_no=f"DEV-VEE-{unique}", utility_service_id=svc.id, read_type="Manual", premise_id="premise-stub")
        db.add(meter); db.flush()

        rule = VeeRule(tenant_id=tenant.id, name="Threshold", utility_service_id=svc.id, read_type="Manual", rule_type="Threshold Alert", parameters={"min_units": 0, "max_units": 100})
        db.add(rule); db.flush()
        config = VeeConfig(tenant_id=tenant.id, name="Config", utility_service_id=svc.id, read_type="Manual")
        db.add(config); db.flush()
        db.add(VeeConfigRule(vee_config_id=config.id, vee_rule_id=rule.id))

        reading = MeterReading(
            tenant_id=tenant.id, meter_id=meter.id, previous_reading=Decimal("100"), previous_reading_date=datetime.date(2026, 1, 1),
            current_reading=Decimal("500"), current_reading_date=datetime.date(2026, 1, 15), source="manual", status="Received",
        )
        db.add(reading)
        db.commit()
        yield {"db": db, "reading": reading}
    finally:
        db.close()


def test_evaluate_reading_resolves_fully_in_one_call(failing_reading):
    """A single evaluate_reading() call on a fresh 'Received' reading must
    reach a terminal status (Completed or Revisit) -- never leave it
    sitting at 'V2', since nothing else calls this interactively without
    the Celery worker running."""
    db = failing_reading["db"]
    reading = evaluate_reading(db, failing_reading["reading"])
    assert reading.status == "Revisit"
