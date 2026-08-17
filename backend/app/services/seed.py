"""
Seed script (CLAUDE.md #32): creates the demo tenant, roles, permissions and
one demo login per seeded role so the whole product can be demonstrated
immediately. Idempotent -- safe to re-run.

Dev-only credentials: see SEED_CREDENTIALS.md. Never hard-code these into
anything that ships to production.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.integration import SmartMeterOem
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.service import TenantService, UtilityService
from app.models.tenant import Tenant
from app.models.user import User
from app.services.rbac_catalog import PERMISSIONS, ROLE_PERMISSION_DEFAULTS, SYSTEM_ROLES

DEMO_TENANT_NAME = "Demo Water Utility"
SEED_PASSWORD = "ChangeMe123!"

# Workbook §7 -- never hard-coded into business logic, only into this seed list.
UTILITY_SERVICE_CATALOGUE = ["Water", "Sewer", "Gas", "Electricity"]
DEMO_TENANT_SERVICES = ["Water", "Sewer"]

# Workbook §24 Smart Meter OEM sheet.
SMART_METER_OEMS: list[dict] = [
    {"name": "Itron", "utility_services": "Electric, gas, water", "highlights": "OpenWay Riva edge computing", "integration_resources": "Distributed Intelligence docs, ACT module PDFs", "links": "https://apps.itron.com/streetlight-vision/"},
    {"name": "Landis+Gyr", "utility_services": "Electric/Gas/Water", "highlights": "DLMS/COSEM, WSDL head-end", "integration_resources": "AIM & Oracle Smart Grid WSDL specs", "links": "https://doc.smart-me.com/products/landis-gyr-module"},
    {"name": "Honeywell/Elster", "utility_services": "Gas, electric", "highlights": "Ultrasonic gas, A1700 meter", "integration_resources": "Technical PDFs/manuals on support portal", "links": "https://developer.honeywellhome.com/api-methods"},
    {"name": "ABB Ltd", "utility_services": "Electric, gas", "highlights": None, "integration_resources": None, "links": "https://library.e.abb.com/public/479c60bf0a4846e7b1e41d9ee25836d4/QAS_3xx1_PH_EN_V1-0_RestAPI.pdf"},
    {"name": "Sensus (Xylem)", "utility_services": "Electric/Gas/Water", "highlights": "CIS sync, analytics modules", "integration_resources": "VFLEX interface, Device/Alarm APIs", "links": "https://www.hillsborough.net/DocumentCenter/View/3664/"},
    {"name": "Badger Meter", "utility_services": "Water", "highlights": None, "integration_resources": None, "links": "https://www.badgermeter.com/service-units-terms-and-conditions/"},
    {"name": "Kamstrup", "utility_services": "Water, electric", "highlights": "Zigbee, DLMS meters", "integration_resources": "DLMS/COSEM protocol via SDK", "links": "https://www.kamstrup.com/en-en/insights/api-access"},
    {"name": "Aclara (Hubbell)", "utility_services": "Gas, electric", "highlights": "SmartPoint-enabled meters", "integration_resources": "AclaraONE Events REST API, technical docs", "links": "https://www.hubbell.com/aclara/en/products/aclaraone-software-solutions/p/12662473"},
]

# email prefix -> (full name, role name or None for SuperAdmin)
DEMO_USERS: list[dict] = [
    {"email": "superadmin@utilityos.dev", "full_name": "Super Admin", "role": None, "is_superadmin": True},
    {"email": "utilityadmin@demo-water.dev", "full_name": "Utility Admin", "role": "Utility Admin"},
    {"email": "csr@demo-water.dev", "full_name": "Demo CSR", "role": "CSR"},
    {"email": "mxmanager@demo-water.dev", "full_name": "Demo MX Manager", "role": "MX Manager"},
    {"email": "bxmanager@demo-water.dev", "full_name": "Demo BX Manager", "role": "BX Manager"},
    {"email": "validator@demo-water.dev", "full_name": "Demo Validator", "role": "Validator"},
    {"email": "supervisor@demo-water.dev", "full_name": "Demo Supervisor", "role": "Supervisor"},
    {"email": "meterreader@demo-water.dev", "full_name": "Demo Meter Reader", "role": "Meter Reader"},
    {"email": "consumer@demo-water.dev", "full_name": "Demo Consumer", "role": "Consumer"},
]


def get_or_create_utility_services(db: Session) -> dict[str, UtilityService]:
    existing = {s.name: s for s in db.execute(select(UtilityService)).scalars().all()}
    for name in UTILITY_SERVICE_CATALOGUE:
        if name not in existing:
            svc = UtilityService(name=name)
            db.add(svc)
            db.flush()
            existing[name] = svc
    return existing


def enable_tenant_services(db: Session, tenant: Tenant, services: dict[str, UtilityService]) -> None:
    enabled = {
        ts.utility_service_id
        for ts in db.execute(select(TenantService).where(TenantService.tenant_id == tenant.id)).scalars()
    }
    for name in DEMO_TENANT_SERVICES:
        svc = services[name]
        if svc.id not in enabled:
            db.add(TenantService(tenant_id=tenant.id, utility_service_id=svc.id, is_enabled=True))


def get_or_create_smart_meter_oems(db: Session) -> None:
    existing = {o.name for o in db.execute(select(SmartMeterOem)).scalars().all()}
    for oem in SMART_METER_OEMS:
        if oem["name"] not in existing:
            db.add(SmartMeterOem(**oem))


def get_or_create_permissions(db: Session) -> dict[tuple[str, str, str], Permission]:
    existing = {(p.module, p.resource, p.action): p for p in db.execute(select(Permission)).scalars().all()}
    for perm in PERMISSIONS:
        key = (perm["module"], perm["resource"], perm["action"])
        if key not in existing:
            row = Permission(**perm)
            db.add(row)
            db.flush()
            existing[key] = row
    return existing


def get_or_create_tenant(db: Session) -> Tenant:
    tenant = db.execute(select(Tenant).where(Tenant.name == DEMO_TENANT_NAME)).scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(
            name=DEMO_TENANT_NAME,
            email="ops@demo-water.dev",
            phone_no="+14155550100",
            address="100 Waterworks Ave, Springfield",
            website="https://demo-water.dev",
            currency="USD",
            timezone="America/New_York",
            date_format="MM/DD/YYYY",
            hst_gst_no="HST-000000000",
            status="active",
        )
        db.add(tenant)
        db.flush()
    return tenant


def get_or_create_roles(db: Session, tenant: Tenant, perms: dict[tuple[str, str, str], Permission]) -> dict[str, Role]:
    existing = {
        r.name: r
        for r in db.execute(select(Role).where((Role.tenant_id == tenant.id) | (Role.tenant_id.is_(None)))).scalars()
    }

    if "SuperAdmin" not in existing:
        role = Role(tenant_id=None, name="SuperAdmin", description="Full system access", is_system=True)
        db.add(role)
        db.flush()
        existing["SuperAdmin"] = role

    for role_def in SYSTEM_ROLES:
        if role_def["name"] not in existing:
            role = Role(tenant_id=tenant.id, name=role_def["name"], description=role_def["description"], is_system=True)
            db.add(role)
            db.flush()
            existing[role_def["name"]] = role

        role_perms = ROLE_PERMISSION_DEFAULTS.get(role_def["name"], [])
        role_id = existing[role_def["name"]].id
        assigned = {
            (rp.role_id, rp.permission_id)
            for rp in db.execute(select(RolePermission).where(RolePermission.role_id == role_id)).scalars()
        }
        for module, resource, action in role_perms:
            perm = perms[(module, resource, action)]
            if (role_id, perm.id) not in assigned:
                db.add(RolePermission(role_id=role_id, permission_id=perm.id))

    return existing


def get_or_create_user(db: Session, tenant: Tenant, roles: dict[str, Role], spec: dict) -> User:
    user = db.execute(select(User).where(User.email == spec["email"])).scalar_one_or_none()
    if user is None:
        user = User(
            tenant_id=None if spec.get("is_superadmin") else tenant.id,
            email=spec["email"],
            full_name=spec["full_name"],
            password_hash=hash_password(SEED_PASSWORD),
            is_superadmin=bool(spec.get("is_superadmin")),
        )
        db.add(user)
        db.flush()

    role_name = "SuperAdmin" if spec.get("is_superadmin") else spec["role"]
    role = roles[role_name]
    already = db.execute(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
    ).scalar_one_or_none()
    if already is None:
        db.add(UserRole(user_id=user.id, role_id=role.id))

    return user


def run_seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        services = get_or_create_utility_services(db)
        get_or_create_smart_meter_oems(db)
        perms = get_or_create_permissions(db)
        tenant = get_or_create_tenant(db)
        enable_tenant_services(db, tenant, services)
        roles = get_or_create_roles(db, tenant, perms)
        for spec in DEMO_USERS:
            get_or_create_user(db, tenant, roles, spec)
        db.commit()
        print(f"Seed complete. Demo tenant: {tenant.name} ({tenant.id})")
        print(f"Seed password for all demo users: {SEED_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
