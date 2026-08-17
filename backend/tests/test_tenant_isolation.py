from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.rbac import Role, UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.services.seed import SEED_PASSWORD

SECOND_TENANT_NAME = "Second Test Utility"
SECOND_USER_EMAIL = "admin@second-utility.dev"


def _create_second_tenant_and_admin():
    db = SessionLocal()
    try:
        tenant = Tenant(name=SECOND_TENANT_NAME, status="active")
        db.add(tenant)
        db.flush()

        role = Role(tenant_id=tenant.id, name="Utility Admin", description="", is_system=True)
        db.add(role)
        db.flush()

        user = User(
            tenant_id=tenant.id,
            email=SECOND_USER_EMAIL,
            full_name="Second Utility Admin",
            password_hash=hash_password(SEED_PASSWORD),
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
        return tenant.id
    finally:
        db.close()


def _login(client, email, password=SEED_PASSWORD):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_tenant_user_only_sees_own_tenant(client):
    second_tenant_id = _create_second_tenant_and_admin()

    token_a = _login(client, "utilityadmin@demo-water.dev")
    resp_a = client.get("/tenants/current", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    tenant_a_id = resp_a.json()["id"]

    token_b = _login(client, SECOND_USER_EMAIL)
    resp_b = client.get("/tenants/current", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    assert resp_b.json()["id"] == second_tenant_id

    assert tenant_a_id != second_tenant_id
    assert resp_a.json()["id"] != resp_b.json()["id"]


def test_tenant_user_cannot_list_all_tenants(client):
    token_a = _login(client, "utilityadmin@demo-water.dev")
    resp = client.get("/admin/tenants", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 403


def test_superadmin_sees_all_tenants(client):
    token = _login(client, "superadmin@utilityos.dev")
    resp = client.get("/admin/tenants", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()}
    assert "Demo Water Utility" in names
    assert SECOND_TENANT_NAME in names


def test_superadmin_has_no_tenant_context(client):
    token = _login(client, "superadmin@utilityos.dev")
    resp = client.get("/tenants/current", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
