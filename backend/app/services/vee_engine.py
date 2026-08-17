"""
VEE engine (workbook §16-17): evaluates a meter_reading against the
VeeRules configured (via VeeConfig) for its meter's utility_service +
read_type, and drives the Received -> V1 -> V2 -> Revisit -> Completed
state machine.

Predefined rule_types (extensible -- "allow additional rule types through
configuration"):
  - "No Reading":      fails if the gap since the previous reading exceeds
                        parameters.max_days_without_reading.
  - "Threshold Alert":  fails if consumption falls outside
                        [parameters.min_units, parameters.max_units].
"""
import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meter import Meter
from app.models.reading import MeterReading
from app.models.vee import VeeConfig, VeeConfigRule, VeeRule, ValidationEvent

DEFAULT_MAX_DAYS_WITHOUT_READING = 45


def _evaluate_no_reading(reading: MeterReading, parameters: dict) -> tuple[bool, str]:
    max_days = parameters.get("max_days_without_reading", DEFAULT_MAX_DAYS_WITHOUT_READING)
    if reading.previous_reading_date is None:
        return True, "No prior reading to compare (first reading) -- pass."
    gap_days = (reading.current_reading_date - reading.previous_reading_date).days
    if gap_days > max_days:
        return False, f"No reading received for {gap_days} days (limit {max_days})."
    return True, "Reading cadence OK."


def _evaluate_threshold_alert(reading: MeterReading, parameters: dict) -> tuple[bool, str]:
    consumption = Decimal(str(reading.current_reading)) - Decimal(str(reading.previous_reading or 0))
    min_units = parameters.get("min_units")
    max_units = parameters.get("max_units")
    if min_units is not None and consumption < Decimal(str(min_units)):
        return False, f"Consumption {consumption} below minimum threshold {min_units}."
    if max_units is not None and consumption > Decimal(str(max_units)):
        return False, f"Consumption {consumption} above maximum threshold {max_units}."
    return True, "Consumption within threshold."


RULE_EVALUATORS = {
    "No Reading": _evaluate_no_reading,
    "Threshold Alert": _evaluate_threshold_alert,
}


def _applicable_rules(db: Session, meter: Meter) -> list[VeeRule]:
    configs = list(
        db.execute(
            select(VeeConfig).where(
                VeeConfig.tenant_id == meter.tenant_id,
                VeeConfig.utility_service_id == meter.utility_service_id,
                VeeConfig.read_type == meter.read_type,
            )
        ).scalars()
    )
    if not configs:
        return []
    config_ids = [c.id for c in configs]
    rule_ids = [
        r[0] for r in db.execute(select(VeeConfigRule.vee_rule_id).where(VeeConfigRule.vee_config_id.in_(config_ids))).all()
    ]
    if not rule_ids:
        return []
    return list(db.execute(select(VeeRule).where(VeeRule.id.in_(rule_ids))).scalars())


def _run_stage(db: Session, reading: MeterReading, meter: Meter, stage: str) -> bool:
    rules = _applicable_rules(db, meter)
    all_passed = True
    now = datetime.datetime.now(datetime.timezone.utc)
    for rule in rules:
        evaluator = RULE_EVALUATORS.get(rule.rule_type)
        if evaluator is None:
            continue  # tenant-configured custom rule type with no evaluator yet -- skip, don't block the pipeline
        passed, message = evaluator(reading, rule.parameters or {})
        db.add(
            ValidationEvent(
                tenant_id=reading.tenant_id, meter_reading_id=reading.id, vee_rule_id=rule.id,
                stage=stage, passed=passed, message=message, evaluated_at=now,
            )
        )
        all_passed = all_passed and passed
    return all_passed


def evaluate_reading(db: Session, reading: MeterReading) -> MeterReading:
    """Runs a reading through the state machine to its next resting state.
    Received -> V1 -> (Completed | V2) -> V2 -> (Completed | Revisit) --
    both stages run in this one call so a reading never gets stranded in
    "V2" waiting for a second call nothing triggers interactively (only the
    VEE Celery Beat sweep would otherwise pick it back up). Readings with
    no applicable VEE config skip straight to Completed."""
    meter = db.get(Meter, reading.meter_id)

    if reading.status == "Received":
        passed = _run_stage(db, reading, meter, "V1")
        reading.status = "Completed" if passed else "V2"

    if reading.status == "V2":
        passed = _run_stage(db, reading, meter, "V2")
        reading.status = "Completed" if passed else "Revisit"

    db.commit()
    db.refresh(reading)
    return reading


def resolve_revisit(db: Session, reading: MeterReading, *, corrected_current_reading: Optional[float] = None) -> MeterReading:
    """Supervisor/CSR correction after a Revisit -- re-enters at V2."""
    if corrected_current_reading is not None:
        reading.current_reading = corrected_current_reading
    reading.status = "V2"
    db.commit()
    return evaluate_reading(db, reading)
