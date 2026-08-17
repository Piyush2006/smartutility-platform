"""
Integration test (CLAUDE.md §33): Create Utility -> Configure -> Consumer
-> Meter -> Reading -> VEE -> Bill, driven entirely through the real HTTP
API (not direct DB access), through everything built by end of Phase 8.
"""
import datetime
import io

SEED_PASSWORD = "ChangeMe123!"


def _login(client, email, password=SEED_PASSWORD):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_full_demo_journey(client):
    # 1. SuperAdmin onboards a new utility + Utility Admin.
    superadmin_headers = _login(client, "superadmin@utilityos.dev")
    resp = client.post(
        "/admin/tenants",
        headers=superadmin_headers,
        json={
            "name": "Journey Test Utility", "phone_no": "+14155550199", "address": "1 Journey Way",
            "website": "https://journey.example.com", "email": "ops@journey.example.com", "currency": "USD",
            "timezone": "America/New_York", "date_format": "MM/DD/YYYY",
            "admin_full_name": "Journey Admin", "admin_email": "journeyadmin@journey.example.com",
        },
    )
    assert resp.status_code == 201, resp.text
    onboarding = resp.json()
    tenant_id = onboarding["tenant"]["id"]
    admin_email = onboarding["admin_email"]
    admin_password = onboarding["temp_password"]

    admin_headers = _login(client, admin_email, admin_password)

    # 2. Enable Water service.
    catalogue = client.get("/services/catalogue", headers=admin_headers).json()
    water = next(s for s in catalogue if s["name"] == "Water")
    resp = client.put("/services/tenant", headers=admin_headers, json={"utility_service_id": water["id"], "is_enabled": True})
    assert resp.status_code == 200

    # 3. Territory: Region -> ... -> Premise.
    region = client.post("/regions", headers=admin_headers, json={"name": "Northeast"}).json()
    country = client.post("/countries", headers=admin_headers, json={"region_id": region["id"], "name": "USA"}).json()
    state = client.post("/states", headers=admin_headers, json={"country_id": country["id"], "name": "NY"}).json()
    city = client.post("/cities", headers=admin_headers, json={"state_id": state["id"], "name": "Springfield"}).json()
    zone = client.post("/zones", headers=admin_headers, json={"city_id": city["id"], "name": "Zone 1"}).json()
    division = client.post("/divisions", headers=admin_headers, json={"zone_id": zone["id"], "name": "Division A"}).json()
    area = client.post("/areas", headers=admin_headers, json={"division_id": division["id"], "name": "Area 1"}).json()
    sub_area = client.post("/sub-areas", headers=admin_headers, json={"area_id": area["id"], "name": "Sub-Area 1", "servicable": True}).json()
    premise = client.post("/premises", headers=admin_headers, json={"sub_area_id": sub_area["id"], "name": "Premise 100", "latitude": 40.0, "longitude": -73.0}).json()
    assert premise["id"]

    # 4. Category / Sub-Category / Rate (tiered) / Plan / Service Charge.
    category = client.post("/categories", headers=admin_headers, json={"name": "Residential"}).json()
    sub_category = client.post("/sub-categories", headers=admin_headers, json={"category_id": category["id"], "name": "Standard"}).json()

    rate = client.post(
        "/rates", headers=admin_headers,
        json={
            "name": "Water Tiered", "rate_type": "variable", "basis": "tiered",
            "tiers": [{"tier_from": 0, "tier_to": 15, "price": 5}, {"tier_from": 15, "tier_to": 30, "price": 6.5}, {"tier_from": 30, "tier_to": None, "price": 7}],
        },
    ).json()
    assert rate["tiers"][0]["price"] == 5.0

    plan = client.post(
        "/plans", headers=admin_headers,
        json={
            "name": "Residential Water Plan", "category_id": category["id"], "sub_category_id": sub_category["id"],
            "tax_percent": 10, "billing_frequency": "monthly", "components": [{"utility_service_id": water["id"], "rate_id": rate["id"]}],
        },
    ).json()
    assert plan["components"][0]["rate_id"] == rate["id"]

    service_charge = client.post(
        "/service-charges", headers=admin_headers, json={"name": "Admin Fee", "utility_service_id": None, "charge_type": "fixed", "rate": 5, "plan_id": plan["id"]},
    ).json()
    assert service_charge["rate"] == 5.0

    # 5. Meter (pre-provisioned inventory).
    meter = client.post(
        "/meters", headers=admin_headers,
        json={"meter_no": "MTR-100", "device_no": "DEV-100", "utility_service_id": water["id"], "read_type": "Manual", "premise_id": premise["id"]},
    ).json()
    assert meter["is_assigned"] is False

    # 6. Consumer (assigns the meter).
    id_doc = client.post(
        "/consumers/id-document", headers=admin_headers, files={"file": ("id.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    ).json()

    resp = client.post(
        "/consumers", headers=admin_headers,
        json={
            "full_name": "Jane Consumer", "contact_no": "+14155550111", "email_address": "jane.consumer@journey.example.com",
            "ssn": "123-45-6789", "id_document_url": id_doc["url"], "premise_id": premise["id"],
            "service_address": "1 Journey Way", "billing_address": "1 Journey Way", "plan_id": plan["id"],
            "activation_date": datetime.date.today().isoformat(), "meter_id": meter["id"],
            "first_meter_reading": 0, "first_meter_reading_date": datetime.date.today().isoformat(),
        },
    )
    assert resp.status_code == 201, resp.text
    consumer_bundle = resp.json()
    consumer = consumer_bundle["consumer"]
    consumer_portal_email = consumer_bundle["portal_email"]
    consumer_portal_password = consumer_bundle["portal_temp_password"]

    meter_after = client.get("/meters", headers=admin_headers).json()
    assert next(m for m in meter_after if m["id"] == meter["id"])["is_assigned"] is True

    # 7. Route -> Read Cycle -> Schedule -> Meter Run.
    route = client.post("/routes", headers=admin_headers, json={"name": "Route 1", "read_type": "Manual", "premise_id": premise["id"], "utility_service_ids": [water["id"]]}).json()
    assert route["meter_count"] == 1  # meter auto-assigned to the route by service+premise match

    read_cycle = client.post("/read-cycles", headers=admin_headers, json={"name": "Cycle 1", "read_type": "Manual", "route_id": route["id"], "utility_service_ids": [water["id"]]}).json()

    schedule = client.post(
        "/meter-schedules", headers=admin_headers,
        json={"read_cycle_id": read_cycle["id"], "recurring": False, "start_date": datetime.date.today().isoformat(), "due_days": 10},
    ).json()

    run = client.post(f"/meter-schedules/{schedule['id']}/generate-run", headers=admin_headers).json()
    assert run["meter_count"] == 1

    # 8. VEE rule/config so the reading actually gets validated.
    vee_rule = client.post(
        "/vee/rules", headers=admin_headers,
        json={"name": "Threshold Check", "utility_service_id": water["id"], "read_type": "Manual", "rule_type": "Threshold Alert", "parameters": {"min_units": 0, "max_units": 100000}},
    ).json()
    client.post("/vee/configs", headers=admin_headers, json={"name": "Water Manual Config", "utility_service_id": water["id"], "read_type": "Manual", "rule_ids": [vee_rule["id"]]})

    # 9. Manual meter reading -> auto-runs VEE -> should complete straight away.
    resp = client.post(
        "/meter-readings", headers=admin_headers,
        json={"meter_id": meter["id"], "meter_run_id": run["id"], "current_reading": 40, "current_reading_date": datetime.date.today().isoformat()},
    )
    assert resp.status_code == 201, resp.text
    reading = resp.json()
    assert reading["status"] == "Completed"

    breakdown = client.get("/meter-readings/validation-breakdown", headers=admin_headers).json()
    cycle_row = next(r for r in breakdown if r["read_cycle_id"] == read_cycle["id"])
    assert cycle_row["completed"] == 1

    # 10. Bill Cycle -> Template -> Schedule -> Run -> Bill -> PDF.
    bill_cycle = client.post("/bill-cycles", headers=admin_headers, json={"name": "Monthly Cycle", "premise_ids": [premise["id"]]}).json()
    assert bill_cycle["consumer_count"] == 1

    bill_template = client.post("/bill-templates", headers=admin_headers, json={"name": "Standard Bill", "template_key": "standard", "fields": []}).json()

    future_gen_date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    bill_schedule = client.post(
        "/bill-schedules", headers=admin_headers,
        json={
            "bill_cycle_id": bill_cycle["id"], "bill_template_id": bill_template["id"], "recurring": False,
            "bill_start_date": (datetime.date.today() - datetime.timedelta(days=30)).isoformat(),
            "bill_end_date": datetime.date.today().isoformat(), "bill_generation_date": future_gen_date, "bill_generation_time": "09:00:00",
        },
    ).json()

    bill_run = client.post(f"/bill-schedules/{bill_schedule['id']}/generate-run", headers=admin_headers).json()
    assert bill_run["status"] == "completed"
    assert bill_run["consumer_count"] == 1

    run_bills = client.get(f"/bill-runs/{bill_run['id']}/bills", headers=admin_headers).json()
    assert len(run_bills) == 1
    bill_row = run_bills[0]
    assert bill_row["consumer_id"] == consumer["id"]
    # tiered rate on 40 units: 15*5 + 15*6.5 + 10*7 = 242.5, + $5 service charge = 247.5, +10% tax = 272.25
    assert bill_row["total_incl_tax"] == 272.25

    pdf_resp = client.get(f"/bills/{bill_row['bill_id']}/pdf", headers=admin_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"

    # 11. Payment against the bill.
    payment = client.post("/payments", headers=admin_headers, json={"bill_id": bill_row["bill_id"], "amount": 100, "method": "e_transfer"}).json()
    assert payment["amount"] == 100.0
    bill_after_payment = client.get(f"/bills/{bill_row['bill_id']}", headers=admin_headers).json()
    assert bill_after_payment["status"] == "partially_paid"

    # 12. Consumer logs in and can see their own bill via the portal -- and nothing else.
    consumer_headers = _login(client, consumer_portal_email, consumer_portal_password)
    portal_dashboard = client.get("/portal/dashboard", headers=consumer_headers).json()
    assert portal_dashboard["consumer_name"] == "Jane Consumer"
    portal_bills = client.get("/portal/bills", headers=consumer_headers).json()
    assert len(portal_bills) == 1
    assert portal_bills[0]["id"] == bill_row["bill_id"]

    # Consumer cannot reach tenant-admin endpoints.
    forbidden = client.get("/consumers", headers=consumer_headers)
    assert forbidden.status_code == 403

    # 13. Tenant isolation: this tenant's admin cannot see the demo tenant's data.
    other_tenant_current = client.get("/tenants/current", headers=admin_headers).json()
    assert other_tenant_current["id"] == tenant_id
    assert other_tenant_current["name"] == "Journey Test Utility"

    # 14. Audit log recorded the utility creation.
    audit = client.get("/admin/audit-logs", headers=superadmin_headers).json()
    assert any(a["entity"] == "Tenant" and a["entity_id"] == tenant_id and a["action"] == "create" for a in audit)
