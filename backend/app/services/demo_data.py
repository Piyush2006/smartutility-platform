"""
Demo showcase data for the "Demo Water Utility" tenant created by seed.py.
Builds a full, realistic dataset end-to-end so the app looks alive out of
the box: territory tree, rates/plans/service charges, consumers + meters,
routes/read-cycles/schedules/runs, 7 rounds of meter readings spanning
~7 months (one deliberately routed to Revisit so the VEE workflow has
something to show) driving 7 bill runs with outstanding carried forward,
PDFs, and a realistic spread of paid/partially-paid/occasionally-missed/
delinquent bills -- enough history for the portal's consumption trend and
bill/payment history to look real, not a 2-point chart.

Idempotent: skips straight to a no-op if it detects it already ran (checks
for the "Pacific Northwest" region on the demo tenant).

    python -m app.services.demo_data
"""
import datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.account import Category, Plan, PlanComponent, Rate, RateTier, ServiceCharge, SubCategory, TouRate
from app.models.billing import (
    Bill,
    BillCycle,
    BillCyclePremise,
    BillSchedule,
    BillTemplate,
    BillTemplateField,
    Payment,
)
from app.models.consumer import Consumer
from app.models.meter import Meter, MeterSchedule, ReadCycle, ReadCycleUtilityService, Route, RouteMeter, RouteUtilityService
from app.models.rbac import Role, UserRole
from app.models.reading import MeterReading
from app.models.service import UtilityService
from app.models.tenant import Tenant
from app.models.territory import Area, City, Country, Division, Premise, Region, State, SubArea, Zone
from app.models.user import User
from app.models.vee import VeeConfig, VeeConfigRule, VeeRule
from app.services.bill_run_engine import generate_bill_run
from app.services.meter_run_engine import generate_meter_run
from app.services.pdf_generator import generate_bill_pdf
from app.services.reading_helpers import get_previous_reading
from app.services.seed import DEMO_TENANT_NAME, SEED_PASSWORD
from app.services.vee_engine import evaluate_reading

TODAY = datetime.date.today()


def _make_reading(db, tenant_id, meter, current_reading, current_date, *, meter_run_id=None, read_cycle_id=None):
    prev_reading, prev_date = get_previous_reading(db, meter.id)
    reading = MeterReading(
        tenant_id=tenant_id, meter_id=meter.id, meter_run_id=meter_run_id, read_cycle_id=read_cycle_id,
        previous_reading=prev_reading, previous_reading_date=prev_date,
        current_reading=current_reading, current_reading_date=current_date,
        source="manual", status="Received", is_duplicate=False,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return evaluate_reading(db, reading)


def _make_consumer_login(db, tenant_id, role_id, full_name, email):
    user = User(tenant_id=tenant_id, email=email, full_name=full_name, password_hash=hash_password(SEED_PASSWORD))
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role_id))
    return user


def run_demo_data() -> None:
    db = SessionLocal()
    try:
        tenant = db.execute(select(Tenant).where(Tenant.name == DEMO_TENANT_NAME)).scalar_one_or_none()
        if tenant is None:
            print("Demo tenant not found -- run `python -m app.services.seed` first.")
            return

        already = db.execute(select(Region).where(Region.tenant_id == tenant.id, Region.name == "Pacific Northwest")).scalar_one_or_none()
        if already is not None:
            print("Demo data already present -- nothing to do.")
            return

        water = db.execute(select(UtilityService).where(UtilityService.name == "Water")).scalar_one()
        sewer = db.execute(select(UtilityService).where(UtilityService.name == "Sewer")).scalar_one()
        consumer_role = db.execute(select(Role).where(Role.tenant_id == tenant.id, Role.name == "Consumer")).scalar_one()
        tid = tenant.id

        # ---- Territory ---------------------------------------------------
        region = Region(tenant_id=tid, name="Pacific Northwest")
        db.add(region); db.flush()
        country = Country(tenant_id=tid, region_id=region.id, name="United States")
        db.add(country); db.flush()
        state = State(tenant_id=tid, country_id=country.id, name="Washington")
        db.add(state); db.flush()
        city = City(tenant_id=tid, state_id=state.id, name="Springfield")
        db.add(city); db.flush()
        zone = Zone(tenant_id=tid, city_id=city.id, name="Zone 1")
        db.add(zone); db.flush()
        division = Division(tenant_id=tid, zone_id=zone.id, name="Division A")
        db.add(division); db.flush()

        premises = []
        area_specs = [
            ("Downtown", "Downtown Core", [("100 Main St", 47.6740, -122.1215), ("102 Main St", 47.6742, -122.1217), ("200 Oak Ave", 47.6751, -122.1230), ("14 Commerce Way", 47.6760, -122.1244)]),
            ("Riverside", "Riverside Heights", [("10 River Rd", 47.6690, -122.1180), ("12 River Rd", 47.6692, -122.1182)]),
        ]
        for area_name, sub_area_name, premise_specs in area_specs:
            area = Area(tenant_id=tid, division_id=division.id, name=area_name)
            db.add(area); db.flush()
            sub_area = SubArea(tenant_id=tid, area_id=area.id, name=sub_area_name, servicable=True)
            db.add(sub_area); db.flush()
            for name, lat, lon in premise_specs:
                premise = Premise(tenant_id=tid, sub_area_id=sub_area.id, name=name, latitude=lat, longitude=lon)
                db.add(premise); db.flush()
                premises.append(premise)

        # ---- Categories / Rates / Plans / Service Charges ------------------
        cat_res = Category(tenant_id=tid, name="Residential"); db.add(cat_res); db.flush()
        cat_com = Category(tenant_id=tid, name="Commercial"); db.add(cat_com); db.flush()
        sub_res = SubCategory(tenant_id=tid, category_id=cat_res.id, name="Single Family"); db.add(sub_res); db.flush()
        sub_com = SubCategory(tenant_id=tid, category_id=cat_com.id, name="Retail"); db.add(sub_com); db.flush()

        rate_water_tiered = Rate(tenant_id=tid, name="Water Tiered Residential", rate_type="variable", basis="tiered")
        db.add(rate_water_tiered); db.flush()
        for lo, hi, price in [(0, 15, 5), (15, 30, 6.5), (30, None, 7)]:
            db.add(RateTier(tenant_id=tid, rate_id=rate_water_tiered.id, tier_from=lo, tier_to=hi, price=price))

        rate_sewer_flat = Rate(tenant_id=tid, name="Sewer Fixed Residential", rate_type="fixed", rate=Decimal("28.00"))
        db.add(rate_sewer_flat); db.flush()

        rate_water_tou = Rate(tenant_id=tid, name="Water TOU Commercial", rate_type="variable", basis="time_of_use")
        db.add(rate_water_tou); db.flush()
        db.add(TouRate(tenant_id=tid, rate_id=rate_water_tou.id, start_time=datetime.time(0, 0), end_time=datetime.time(16, 0), price=Decimal("4.5784")))
        db.add(TouRate(tenant_id=tid, rate_id=rate_water_tou.id, start_time=datetime.time(16, 0), end_time=datetime.time(0, 0), price=Decimal("5.67")))

        plan_res_water = Plan(tenant_id=tid, name="Residential Water Tiered", category_id=cat_res.id, sub_category_id=sub_res.id, tax_percent=Decimal("8.50"), billing_frequency="monthly")
        db.add(plan_res_water); db.flush()
        db.add(PlanComponent(tenant_id=tid, plan_id=plan_res_water.id, utility_service_id=water.id, rate_id=rate_water_tiered.id))

        plan_res_sewer = Plan(tenant_id=tid, name="Residential Sewer Fixed", category_id=cat_res.id, sub_category_id=sub_res.id, tax_percent=Decimal("8.50"), billing_frequency="monthly")
        db.add(plan_res_sewer); db.flush()
        db.add(PlanComponent(tenant_id=tid, plan_id=plan_res_sewer.id, utility_service_id=sewer.id, rate_id=rate_sewer_flat.id))

        plan_com_water = Plan(tenant_id=tid, name="Commercial Water TOU", category_id=cat_com.id, sub_category_id=sub_com.id, tax_percent=Decimal("8.50"), billing_frequency="monthly")
        db.add(plan_com_water); db.flush()
        db.add(PlanComponent(tenant_id=tid, plan_id=plan_com_water.id, utility_service_id=water.id, rate_id=rate_water_tou.id))

        db.add(ServiceCharge(tenant_id=tid, name="Admin Fee", utility_service_id=None, charge_type="fixed", rate=Decimal("5.00"), plan_id=plan_res_water.id))
        db.add(ServiceCharge(tenant_id=tid, name="Admin Fee", utility_service_id=None, charge_type="fixed", rate=Decimal("5.00"), plan_id=plan_res_sewer.id))
        db.add(ServiceCharge(tenant_id=tid, name="Meter Maintenance", utility_service_id=water.id, charge_type="fixed", rate=Decimal("3.00"), plan_id=plan_com_water.id))
        db.commit()

        # ---- Meters + Consumers -------------------------------------------
        consumer_specs = [
            ("Emma Rodriguez", premises[0], water, plan_res_water, 1000.0, 40),
            ("Liam Chen", premises[0], water, plan_res_water, 850.0, 22),
            ("Olivia Patel", premises[1], water, plan_res_water, 1200.0, 12),
            ("Noah Thompson", premises[2], water, plan_res_water, 500.0, 28),
            ("Ava Martinez", premises[3], water, plan_com_water, 3000.0, 300),
            ("Ethan Kim", premises[4], sewer, plan_res_sewer, 400.0, 18),
        ]
        # 7 reading/bill rounds spanning ~7 months so the consumer portal's
        # consumption chart and bill/payment history show a real trend
        # instead of 2 flat data points.
        first_reading_date = TODAY - datetime.timedelta(days=210)
        round_offsets = [180, 150, 120, 90, 60, 30, 3]
        round_dates = [TODAY - datetime.timedelta(days=d) for d in round_offsets]
        # Shared seasonal curve applied on top of each consumer's own
        # baseline monthly_units -- capped at 1.2x so Ava's 300-unit
        # commercial baseline never crosses the 400-unit VEE threshold
        # (only Noah's round-2 spike is meant to trigger Revisit).
        SEASONAL_MULTIPLIERS = [0.85, 1.05, 1.20, 1.15, 0.90, 0.75, 1.10]

        created_consumers = []
        for i, (full_name, premise, service, plan, baseline, monthly_units) in enumerate(consumer_specs, start=1):
            meter = Meter(
                tenant_id=tid, meter_no=f"MTR-{100 + i}", device_no=f"DEV-DEMO-{100 + i}",
                utility_service_id=service.id, read_type="Manual", premise_id=premise.id,
                installation_date=first_reading_date, is_assigned=True,
            )
            db.add(meter); db.flush()

            slug = full_name.lower().replace(" ", ".")
            email = f"{slug}@demo-water.dev"
            user = _make_consumer_login(db, tid, consumer_role.id, full_name, email)
            db.flush()

            consumer = Consumer(
                tenant_id=tid, user_id=user.id, full_name=full_name, contact_no=f"+1415555{1000 + i:04d}",
                email_address=email, ssn=f"12{i}-45-678{i}", id_document_url="/uploads/consumer-ids/demo-placeholder.pdf",
                premise_id=premise.id, service_address=premise.name, billing_address=premise.name,
                plan_id=plan.id, activation_date=first_reading_date, meter_id=meter.id,
                first_meter_reading=baseline, first_meter_reading_date=first_reading_date, status="active",
            )
            db.add(consumer)
            db.commit()
            created_consumers.append({"consumer": consumer, "meter": meter, "premise": premise, "service": service, "baseline": baseline, "monthly_units": monthly_units})

        # ---- Routes / Read Cycles / Schedules / Runs (grouped by premise) --
        premise_ids_with_meters = {c["premise"].id for c in created_consumers}
        runs_by_premise = {}
        for premise_id in premise_ids_with_meters:
            meters_here = [c["meter"] for c in created_consumers if c["premise"].id == premise_id]
            services_here = list({m.utility_service_id for m in meters_here})
            premise_name = next(c["premise"].name for c in created_consumers if c["premise"].id == premise_id)

            route = Route(tenant_id=tid, name=f"Route - {premise_name}", read_type="Manual", premise_id=premise_id)
            db.add(route); db.flush()
            for sid in services_here:
                db.add(RouteUtilityService(route_id=route.id, utility_service_id=sid))
            for m in meters_here:
                db.add(RouteMeter(route_id=route.id, meter_id=m.id))

            read_cycle = ReadCycle(tenant_id=tid, name=f"Cycle - {premise_name}", read_type="Manual", route_id=route.id)
            db.add(read_cycle); db.flush()
            for sid in services_here:
                db.add(ReadCycleUtilityService(read_cycle_id=read_cycle.id, utility_service_id=sid))

            schedule = MeterSchedule(tenant_id=tid, read_cycle_id=read_cycle.id, recurring=False, start_date=first_reading_date, due_days=10, is_active=True)
            db.add(schedule)
            db.commit()

            run = generate_meter_run(db, schedule)
            runs_by_premise[premise_id] = {"run": run, "read_cycle_id": read_cycle.id}

        # ---- VEE rules/config (Water + Sewer, Manual) -----------------------
        for svc in (water, sewer):
            rule_threshold = VeeRule(tenant_id=tid, name=f"{svc.name} Threshold Check", utility_service_id=svc.id, read_type="Manual", rule_type="Threshold Alert", parameters={"min_units": 0, "max_units": 400})
            rule_no_reading = VeeRule(tenant_id=tid, name=f"{svc.name} No Reading Check", utility_service_id=svc.id, read_type="Manual", rule_type="No Reading", parameters={"max_days_without_reading": 60})
            db.add_all([rule_threshold, rule_no_reading]); db.flush()
            config = VeeConfig(tenant_id=tid, name=f"{svc.name} Manual Config", utility_service_id=svc.id, read_type="Manual")
            db.add(config); db.flush()
            db.add(VeeConfigRule(vee_config_id=config.id, vee_rule_id=rule_threshold.id))
            db.add(VeeConfigRule(vee_config_id=config.id, vee_rule_id=rule_no_reading.id))
        db.commit()

        bill_cycle = BillCycle(tenant_id=tid, name="Monthly Cycle - All Premises")
        db.add(bill_cycle); db.flush()
        for premise_id in premise_ids_with_meters:
            db.add(BillCyclePremise(bill_cycle_id=bill_cycle.id, premise_id=premise_id))

        bill_template = BillTemplate(tenant_id=tid, name="Standard Bill", template_key="standard")
        db.add(bill_template); db.flush()
        for i, field_key in enumerate([
            "account_no", "account_name", "invoice_date", "due_date", "service_address", "meter_number",
            "prev_reading", "current_reading", "usage", "rate", "base_charge", "tax_amount", "total_incl_tax", "total_outstanding",
        ]):
            db.add(BillTemplateField(tenant_id=tid, bill_template_id=bill_template.id, field_key=field_key, is_enabled=True, sort_order=i))
        db.commit()

        # ---- 7 rounds of readings -> 7 bill runs, one per round ------------
        # Round index 1 is Noah's Water meter spiking into Revisit (workbook
        # VEE demo); he's then deliberately left unread for every later
        # round -- a real "stuck until someone resolves the Revisit"
        # consumer -- so his bills keep re-billing his last Completed
        # reading with outstanding compounding, unpaid.
        #
        # Payment behavior is applied round-by-round (not just on the final
        # bill) so previous_outstanding actually carries forward
        # differently per consumer: Emma/Ava always pay in full, Liam pays
        # half every time, Olivia pays in full but misses every 3rd bill,
        # Ethan and Noah never pay -- a realistic paid / partially-paid /
        # occasionally-missed / delinquent spread for the dashboards and
        # the portal's payment history.
        PAYMENT_POLICY = {"Emma Rodriguez": "full_every", "Liam Chen": "partial_every", "Olivia Patel": "full_skip_third", "Ava Martinez": "full_every"}
        bill_runs = []
        for round_idx, round_date in enumerate(round_dates):
            for c in created_consumers:
                if c["consumer"].full_name == "Noah Thompson" and round_idx > 1:
                    continue
                run_info = runs_by_premise[c["premise"].id]
                prev_current, _ = get_previous_reading(db, c["meter"].id)
                base = float(prev_current) if prev_current is not None else c["baseline"]
                if c["consumer"].full_name == "Noah Thompson" and round_idx == 1:
                    units = 5000  # deliberately blows the 400-unit threshold -> V1 fail -> V2 fail -> Revisit
                else:
                    units = round(c["monthly_units"] * SEASONAL_MULTIPLIERS[round_idx])
                current = base + units
                _make_reading(db, tid, c["meter"], current, round_date, meter_run_id=run_info["run"].id, read_cycle_id=run_info["read_cycle_id"])

            schedule = BillSchedule(
                tenant_id=tid, bill_cycle_id=bill_cycle.id, bill_template_id=bill_template.id, recurring=True, frequency="Monthly",
                bill_start_date=(round_dates[round_idx - 1] if round_idx > 0 else first_reading_date), bill_end_date=round_date,
                bill_generation_date=round_date, bill_generation_time=datetime.time(9, 0), description=f"Round {round_idx + 1} (auto-generated by demo data)",
            )
            db.add(schedule)
            db.commit()
            run = generate_bill_run(db, schedule)
            for bill in db.execute(select(Bill).where(Bill.bill_run_id == run.id)).scalars():
                bill.pdf_url = generate_bill_pdf(db, bill)
            db.commit()
            bill_runs.append(run)

            for c in created_consumers:
                policy = PAYMENT_POLICY.get(c["consumer"].full_name)
                if not policy:
                    continue  # Noah (stuck in Revisit) and Ethan (delinquent) never pay
                if policy == "full_skip_third" and (round_idx + 1) % 3 == 0:
                    continue
                bill = db.execute(select(Bill).where(Bill.consumer_id == c["consumer"].id, Bill.bill_run_id == run.id)).scalars().first()
                if bill is None or float(bill.total_outstanding) <= 0:
                    continue
                fraction = 0.5 if policy == "partial_every" else 1.0
                amount = round(float(bill.total_outstanding) * fraction, 2)
                db.add(Payment(
                    tenant_id=tid, bill_id=bill.id, consumer_id=c["consumer"].id, amount=amount,
                    method="e_transfer", paid_at=datetime.datetime.now(datetime.timezone.utc), reference=f"DEMO-PAY-{c['consumer'].id[:8]}-{round_idx + 1}",
                ))
                bill.status = "paid" if amount >= float(bill.total_outstanding) else "partially_paid"
            db.commit()

        print(f"Demo data created for tenant '{tenant.name}':")
        print(f"  - {len(premises)} premises across 2 areas")
        print(f"  - {len(created_consumers)} consumers/meters, {len(runs_by_premise)} routes/cycles/runs")
        print(f"  - {len(bill_runs)} rounds of readings + bill runs (outstanding carried forward)")
        print("  - Noah Thompson's 2nd Water reading is stuck in Revisit -- try resolving it in the UI")
        print("  - Payments: Emma Rodriguez & Ava Martinez (always paid in full), Liam Chen (always partial),")
        print("    Olivia Patel (pays in full, misses every 3rd bill), Ethan Kim (never pays -- delinquent)")
        print(f"  - Consumer portal logins: <firstname>.<lastname>@demo-water.dev / {SEED_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    run_demo_data()
