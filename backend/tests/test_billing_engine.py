import datetime
import uuid
from decimal import Decimal

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.account import Category, Plan, PlanComponent, Rate, RateTier, ServiceCharge, SubCategory
from app.models.consumer import Consumer
from app.models.meter import Meter
from app.models.reading import MeterReading
from app.models.service import UtilityService
from app.models.tenant import Tenant
from app.services.billing_engine import BillingError, compute_bill, compute_consumption, compute_outstanding, generate_bill

import pytest


@pytest.fixture
def billing_fixture():
    """Builds one tenant with a fixed-rate plan + a $10 fixed service
    charge + a consumer/meter/reading, entirely in the test DB."""
    db = SessionLocal()
    try:
        tenant = Tenant(name="Billing Test Utility", status="active")
        db.add(tenant)
        db.flush()

        svc = db.query(UtilityService).filter_by(name="Water").first()
        if svc is None:
            svc = UtilityService(name="Water")
            db.add(svc)
            db.flush()

        category = Category(tenant_id=tenant.id, name="Residential")
        db.add(category)
        db.flush()
        sub_category = SubCategory(tenant_id=tenant.id, category_id=category.id, name="Standard")
        db.add(sub_category)
        db.flush()

        rate = Rate(tenant_id=tenant.id, name="Water Fixed", rate_type="fixed", rate=Decimal("25.00"))
        db.add(rate)
        db.flush()

        plan = Plan(tenant_id=tenant.id, name="Basic Water Plan", category_id=category.id, sub_category_id=sub_category.id, tax_percent=Decimal("10.00"))
        db.add(plan)
        db.flush()
        db.add(PlanComponent(tenant_id=tenant.id, plan_id=plan.id, utility_service_id=svc.id, rate_id=rate.id))

        db.add(ServiceCharge(tenant_id=tenant.id, name="Admin Fee", utility_service_id=None, charge_type="fixed", rate=Decimal("5.00"), plan_id=plan.id))

        unique = uuid.uuid4().hex[:8]
        meter = Meter(tenant_id=tenant.id, meter_no="M-1", device_no=f"DEV-BILL-{unique}", utility_service_id=svc.id, read_type="Manual", premise_id="premise-stub")
        db.add(meter)
        db.flush()

        from app.models.user import User as UserModel
        email = f"billingtest-{unique}@demo.dev"
        user = UserModel(tenant_id=tenant.id, email=email, full_name="Billing Test Consumer", password_hash=hash_password("x"))
        db.add(user)
        db.flush()

        consumer = Consumer(
            tenant_id=tenant.id, full_name="Billing Test Consumer", contact_no="+14155550111", email_address=email,
            ssn="123-45-6789", id_document_url="/uploads/x.pdf", premise_id="premise-stub", service_address="1 Test St",
            billing_address="1 Test St", plan_id=plan.id, activation_date=datetime.date.today(), meter_id=meter.id,
            first_meter_reading=0, first_meter_reading_date=datetime.date.today(), user_id=user.id,
        )
        db.add(consumer)
        db.flush()

        reading = MeterReading(
            tenant_id=tenant.id, meter_id=meter.id, previous_reading=Decimal("100"), previous_reading_date=datetime.date(2026, 1, 1),
            current_reading=Decimal("150"), current_reading_date=datetime.date(2026, 2, 1), source="manual", status="Completed",
        )
        db.add(reading)
        db.commit()

        yield {"db": db, "tenant": tenant, "consumer": consumer, "reading": reading, "plan": plan}
    finally:
        db.close()


def test_compute_consumption():
    reading = MeterReading(current_reading=Decimal("150"), previous_reading=Decimal("100"))
    assert compute_consumption(reading) == Decimal("50")


def test_compute_consumption_rejects_negative():
    reading = MeterReading(current_reading=Decimal("90"), previous_reading=Decimal("100"))
    with pytest.raises(BillingError):
        compute_consumption(reading)


def test_compute_bill_totals(billing_fixture):
    db = billing_fixture["db"]
    computation = compute_bill(
        db, consumer=billing_fixture["consumer"], reading=billing_fixture["reading"],
        service_period_start=datetime.date(2026, 1, 1), service_period_end=datetime.date(2026, 2, 1),
    )
    # fixed rate charge = $25.00 (consumption is irrelevant for fixed rate_type)
    assert computation.base_charge == Decimal("25.00")
    # + $5.00 fixed service charge = $30.00 subtotal
    assert computation.service_charges_total == Decimal("5.00")
    assert computation.total_excl_tax == Decimal("30.00")
    # 10% tax on $30.00 = $3.00
    assert computation.tax_amount == Decimal("3.00")
    assert computation.total_incl_tax == Decimal("33.00")
    # No prior bill -> no outstanding carried forward
    assert computation.previous_outstanding == Decimal("0.00")
    assert computation.total_outstanding == Decimal("33.00")


def test_generate_bill_persists_and_carries_outstanding(billing_fixture):
    db = billing_fixture["db"]
    bill1 = generate_bill(
        db, bill_run_id="run-1", consumer=billing_fixture["consumer"], reading=billing_fixture["reading"],
        service_period_start=datetime.date(2026, 1, 1), service_period_end=datetime.date(2026, 2, 1),
    )
    assert bill1.total_incl_tax == Decimal("33.00")
    assert bill1.total_outstanding == Decimal("33.00")
    assert bill1.invoice_no.startswith("INV-")

    # A second bill period with no payments made against bill1 carries its
    # full outstanding balance forward.
    reading2 = MeterReading(
        tenant_id=billing_fixture["tenant"].id, meter_id=billing_fixture["consumer"].meter_id,
        previous_reading=Decimal("150"), previous_reading_date=datetime.date(2026, 2, 1),
        current_reading=Decimal("200"), current_reading_date=datetime.date(2026, 3, 1), source="manual", status="Completed",
    )
    db.add(reading2)
    db.commit()

    outstanding = compute_outstanding(db, billing_fixture["consumer"].id)
    assert outstanding == Decimal("33.00")

    bill2 = generate_bill(
        db, bill_run_id="run-2", consumer=billing_fixture["consumer"], reading=reading2,
        service_period_start=datetime.date(2026, 2, 1), service_period_end=datetime.date(2026, 3, 1),
    )
    assert bill2.previous_outstanding == Decimal("33.00")
    assert bill2.total_outstanding == Decimal("66.00")  # 33 carried + 33 new
