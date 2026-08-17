"""
Billing engine (CLAUDE.md §20): turns one consumer's latest completed
meter reading + plan into a persisted Bill. Runs entirely server-side --
never in the frontend -- and is deterministic given its inputs (unit
tested in tests/test_billing_engine.py).

    Consumption = Current Reading - Previous Reading
    1. identify consumer plan
    2. identify applicable utility service (via meter -> plan component)
    3. identify effective rate (plan component's Rate row)
    4. calculate fixed/per-unit/tiered/TOU charge (rate_engine)
    5. add service charges
    6. calculate tax
    7. apply credits/debits
    8. calculate total
    9. apply previous outstanding/payments
    10. generate bill
"""
import dataclasses
import datetime
import secrets
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Plan, PlanComponent, Rate, RateTier, ServiceCharge, TouRate
from app.models.billing import Bill, BillLineItem, Payment
from app.models.consumer import Consumer
from app.models.meter import Meter
from app.models.reading import MeterReading
from app.services.rate_engine import TierSpec, TouSpec, calculate_consumption_charge, calculate_service_charge, calculate_tax, round_money


class BillingError(ValueError):
    pass


@dataclasses.dataclass
class BillComputation:
    consumption: Decimal
    base_charge: Decimal
    service_charges_total: Decimal
    line_items: list[dict]
    tax_amount: Decimal
    total_excl_tax: Decimal
    total_incl_tax: Decimal
    previous_outstanding: Decimal
    total_outstanding: Decimal


def _rate_spec(db: Session, rate: Rate):
    tiers = None
    tou = None
    if rate.rate_type == "variable" and rate.basis == "tiered":
        tiers = [
            TierSpec(Decimal(str(t.tier_from)), Decimal(str(t.tier_to)) if t.tier_to is not None else None, Decimal(str(t.price)))
            for t in db.execute(select(RateTier).where(RateTier.rate_id == rate.id)).scalars()
        ]
    if rate.rate_type == "variable" and rate.basis == "time_of_use":
        tou = [
            TouSpec(t.start_time, t.end_time, Decimal(str(t.price)))
            for t in db.execute(select(TouRate).where(TouRate.rate_id == rate.id)).scalars()
        ]
    return tiers, tou


def compute_consumption(reading: MeterReading) -> Decimal:
    current = Decimal(str(reading.current_reading))
    previous = Decimal(str(reading.previous_reading)) if reading.previous_reading is not None else Decimal("0")
    consumption = current - previous
    if consumption < 0:
        raise BillingError("Current reading is lower than previous reading -- cannot bill negative consumption.")
    return consumption


def compute_outstanding(db: Session, consumer_id: str, *, excluding_bill_id: Optional[str] = None) -> Decimal:
    """previous_outstanding = latest prior bill's total_outstanding minus
    any payments recorded since that bill was issued. Ordered by created_at
    (a real timestamp) as well as invoice_date -- multiple bills generated
    on the same calendar day would otherwise have an ambiguous tiebreak on
    invoice_date alone."""
    stmt = select(Bill).where(Bill.consumer_id == consumer_id).order_by(Bill.invoice_date.desc(), Bill.created_at.desc())
    if excluding_bill_id:
        stmt = stmt.where(Bill.id != excluding_bill_id)
    prior_bill = db.execute(stmt).scalars().first()
    if prior_bill is None:
        return Decimal("0.00")

    payments = db.execute(select(Payment).where(Payment.bill_id == prior_bill.id)).scalars()
    paid = sum((Decimal(str(p.amount)) for p in payments), Decimal("0"))
    remaining = Decimal(str(prior_bill.total_outstanding)) - paid
    return max(remaining, Decimal("0.00"))


def compute_bill(
    db: Session,
    *,
    consumer: Consumer,
    reading: MeterReading,
    service_period_start: datetime.date,
    service_period_end: datetime.date,
    late_charges: Decimal = Decimal("0"),
    credit_note: Decimal = Decimal("0"),
    debit_note: Decimal = Decimal("0"),
) -> BillComputation:
    plan = db.get(Plan, consumer.plan_id)
    if plan is None:
        raise BillingError("Consumer has no plan assigned.")
    meter = db.get(Meter, consumer.meter_id)
    if meter is None:
        raise BillingError("Consumer has no meter assigned.")

    component = db.execute(
        select(PlanComponent).where(PlanComponent.plan_id == plan.id, PlanComponent.utility_service_id == meter.utility_service_id)
    ).scalars().first()
    if component is None:
        raise BillingError(f"Plan '{plan.name}' has no rate configured for this consumer's utility service.")
    rate = db.get(Rate, component.rate_id)

    consumption = compute_consumption(reading)
    tiers, tou = _rate_spec(db, rate)
    base_charge = calculate_consumption_charge(
        rate_type=rate.rate_type, rate=Decimal(str(rate.rate)) if rate.rate is not None else None,
        basis=rate.basis, consumption=consumption, tiers=tiers, tou_windows=tou,
    )

    line_items = [{"label": f"{rate.name} usage charge", "kind": "usage", "amount": str(base_charge)}]

    service_charges_total = Decimal("0.00")
    charges = db.execute(
        select(ServiceCharge).where(
            ServiceCharge.tenant_id == consumer.tenant_id,
            (ServiceCharge.plan_id == plan.id) | (ServiceCharge.plan_id.is_(None)),
            (ServiceCharge.utility_service_id == meter.utility_service_id) | (ServiceCharge.utility_service_id.is_(None)),
        )
    ).scalars()
    for charge in charges:
        amount = calculate_service_charge(charge_type=charge.charge_type, rate=Decimal(str(charge.rate)), consumption=consumption)
        service_charges_total += amount
        line_items.append({"label": charge.name, "kind": "service_charge", "amount": str(amount)})

    subtotal = base_charge + service_charges_total
    tax_amount = calculate_tax(subtotal, Decimal(str(plan.tax_percent)) if plan.tax_percent is not None else None)
    if tax_amount:
        line_items.append({"label": "Tax", "kind": "tax", "amount": str(tax_amount)})

    total_excl_tax = round_money(subtotal)
    total_incl_tax = round_money(subtotal + tax_amount)

    if credit_note:
        line_items.append({"label": "Credit note", "kind": "credit", "amount": str(-abs(credit_note))})
    if debit_note:
        line_items.append({"label": "Debit note", "kind": "debit", "amount": str(debit_note)})
    if late_charges:
        line_items.append({"label": "Late charges", "kind": "late_fee", "amount": str(late_charges)})

    previous_outstanding = compute_outstanding(db, consumer.id)
    total_outstanding = round_money(previous_outstanding + total_incl_tax + late_charges - credit_note + debit_note)

    return BillComputation(
        consumption=consumption, base_charge=base_charge, service_charges_total=round_money(service_charges_total),
        line_items=line_items, tax_amount=tax_amount, total_excl_tax=total_excl_tax, total_incl_tax=total_incl_tax,
        previous_outstanding=previous_outstanding, total_outstanding=total_outstanding,
    )


def generate_bill(
    db: Session, *, bill_run_id: str, consumer: Consumer, reading: MeterReading,
    service_period_start: datetime.date, service_period_end: datetime.date, due_days: int = 21,
) -> Bill:
    computation = compute_bill(db, consumer=consumer, reading=reading, service_period_start=service_period_start, service_period_end=service_period_end)
    meter = db.get(Meter, consumer.meter_id)

    invoice_date = datetime.date.today()
    invoice_no = f"INV-{invoice_date.strftime('%Y%m')}-{secrets.token_hex(4).upper()}"

    data_snapshot = {
        "account_no": consumer.id,
        "account_name": consumer.full_name,
        "phone_no": consumer.contact_no,
        "email": consumer.email_address,
        "service_period": f"{service_period_start.isoformat()} - {service_period_end.isoformat()}",
        "invoice_date": invoice_date.isoformat(),
        "invoice_no": invoice_no,
        "service_address": consumer.service_address,
        "billing_address": consumer.billing_address,
        "meter_id": consumer.meter_id,
        "meter_no": meter.meter_no if meter else consumer.meter_id,
        "device_no": meter.device_no if meter else None,
        "previous_reading": str(reading.previous_reading) if reading.previous_reading is not None else None,
        "previous_reading_date": reading.previous_reading_date.isoformat() if reading.previous_reading_date else None,
        "current_reading": str(reading.current_reading),
        "current_reading_date": reading.current_reading_date.isoformat(),
        "days_current_minus_prev": (reading.current_reading_date - reading.previous_reading_date).days if reading.previous_reading_date else None,
        "usage": str(computation.consumption),
        "base_charge": str(computation.base_charge),
        "service_charges_total": str(computation.service_charges_total),
        "tax_amount": str(computation.tax_amount),
        "total_excl_tax": str(computation.total_excl_tax),
        "total_incl_tax": str(computation.total_incl_tax),
        "previous_outstanding": str(computation.previous_outstanding),
        "total_outstanding": str(computation.total_outstanding),
        "line_items": computation.line_items,
    }

    bill = Bill(
        tenant_id=consumer.tenant_id, bill_run_id=bill_run_id, consumer_id=consumer.id, invoice_no=invoice_no,
        invoice_date=invoice_date, due_date=invoice_date + datetime.timedelta(days=due_days),
        service_period_start=service_period_start, service_period_end=service_period_end,
        usage=computation.consumption, base_charge=computation.base_charge,
        service_charges_total=computation.service_charges_total, tax_amount=computation.tax_amount,
        total_excl_tax=computation.total_excl_tax, total_incl_tax=computation.total_incl_tax,
        previous_outstanding=computation.previous_outstanding, late_charges=Decimal("0"),
        credit_note=Decimal("0"), debit_note=Decimal("0"), total_outstanding=computation.total_outstanding,
        status="issued", data=data_snapshot,
    )
    db.add(bill)
    db.flush()
    for item in computation.line_items:
        db.add(BillLineItem(tenant_id=consumer.tenant_id, bill_id=bill.id, label=item["label"], kind=item["kind"], amount=Decimal(item["amount"])))
    db.commit()
    db.refresh(bill)
    return bill
