from urllib.parse import parse_qs, urlparse

from app.services.seed import SEED_PASSWORD


def _login(client, email, password=SEED_PASSWORD):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _activate_invite(client, invite_link, password="BrandNewPassword123"):
    """Extracts the token from an invite_link (as the emailed link would
    encode it) and completes the set-your-own-password flow, returning
    ready-to-use auth headers for the newly activated account."""
    token = parse_qs(urlparse(invite_link).query)["token"][0]
    resp = client.post("/auth/set-password", json={"token": token, "new_password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_utility_admin_can_list_roles_and_invite_staff_user(client):
    headers = _login(client, "utilityadmin@demo-water.dev")

    roles = client.get("/roles", headers=headers).json()
    csr_role = next(r for r in roles if r["name"] == "CSR")

    resp = client.post("/users", headers=headers, json={"full_name": "New CSR Hire", "email": "new.csr.hire@demo-water.dev", "role_id": csr_role["id"]})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["email"] == "new.csr.hire@demo-water.dev"
    assert body["user"]["roles"][0]["name"] == "CSR"
    assert body["invite_link"]
    assert body["email_sent"] is False  # no SMTP configured in tests

    # the invited user cannot log in until they set a password via the invite link
    assert client.post("/auth/login", json={"email": "new.csr.hire@demo-water.dev", "password": "anything"}).status_code == 401

    new_user_headers = _activate_invite(client, body["invite_link"])
    me = client.get("/auth/me", headers=new_user_headers).json()
    assert me["roles"][0]["name"] == "CSR"

    # and the chosen password now works for a normal login too
    assert client.post("/auth/login", json={"email": "new.csr.hire@demo-water.dev", "password": "BrandNewPassword123"}).status_code == 200


def test_set_password_rejects_reused_or_invalid_token(client):
    headers = _login(client, "utilityadmin@demo-water.dev")
    roles = client.get("/roles", headers=headers).json()
    csr_role = next(r for r in roles if r["name"] == "CSR")
    invited = client.post("/users", headers=headers, json={"full_name": "One Time", "email": "one.time@demo-water.dev", "role_id": csr_role["id"]}).json()

    _activate_invite(client, invited["invite_link"], password="FirstPassword123")

    resp = client.post("/auth/set-password", json={"token": "not-a-real-token", "new_password": "Whatever123"})
    assert resp.status_code == 400


def test_edit_user_reassigns_role_and_can_deactivate(client):
    headers = _login(client, "utilityadmin@demo-water.dev")
    roles = {r["name"]: r["id"] for r in client.get("/roles", headers=headers).json()}

    invited = client.post("/users", headers=headers, json={"full_name": "Reassign Me", "email": "reassign.me@demo-water.dev", "role_id": roles["CSR"]}).json()
    user_id = invited["user"]["id"]

    resp = client.patch(f"/users/{user_id}", headers=headers, json={"role_id": roles["MX Manager"]})
    assert resp.status_code == 200
    assert resp.json()["roles"][0]["name"] == "MX Manager"

    resp = client.patch(f"/users/{user_id}", headers=headers, json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_csr_cannot_manage_users(client):
    """CSR only has consumer+reports permissions -- not users."""
    headers = _login(client, "csr@demo-water.dev")
    resp = client.get("/users", headers=headers)
    assert resp.status_code == 403


def test_consumer_role_users_excluded_from_staff_list(client):
    headers = _login(client, "utilityadmin@demo-water.dev")
    users = client.get("/users", headers=headers).json()
    assert all(not (len(u["roles"]) == 1 and u["roles"][0]["name"] == "Consumer") for u in users)


def test_create_custom_role_and_assign_it(client):
    headers = _login(client, "utilityadmin@demo-water.dev")
    permissions = client.get("/permissions", headers=headers).json()
    billing_view = next(p for p in permissions if p["module"] == "billing" and p["action"] == "view")
    reading_view = next(p for p in permissions if p["module"] == "reading" and p["action"] == "view")

    resp = client.post(
        "/roles", headers=headers,
        json={"name": "Billing Read-Only", "description": "Can see bills but not touch anything else", "permission_ids": [billing_view["id"], reading_view["id"]]},
    )
    assert resp.status_code == 201, resp.text
    role = resp.json()
    assert role["is_system"] is False
    assert len(role["permissions"]) == 2

    invited = client.post("/users", headers=headers, json={"full_name": "Read Only Person", "email": "readonly@demo-water.dev", "role_id": role["id"]}).json()
    new_headers = _activate_invite(client, invited["invite_link"])
    me = client.get("/auth/me", headers=new_headers).json()
    assert set(me["permission_modules"]) == {"billing", "reading"}

    # can view bills, but not create/edit them
    assert client.get("/bills", headers=new_headers).status_code == 200
    assert client.post("/bill-cycles", headers=new_headers, json={"name": "x", "premise_ids": []}).status_code == 403


def test_system_roles_cannot_be_edited_or_deleted(client):
    headers = _login(client, "utilityadmin@demo-water.dev")
    csr_role = next(r for r in client.get("/roles", headers=headers).json() if r["name"] == "CSR")

    assert client.patch(f"/roles/{csr_role['id']}", headers=headers, json={"name": "Renamed"}).status_code == 400
    assert client.delete(f"/roles/{csr_role['id']}", headers=headers).status_code == 400


def test_custom_role_cannot_be_deleted_while_assigned(client):
    headers = _login(client, "utilityadmin@demo-water.dev")
    permissions = client.get("/permissions", headers=headers).json()
    view_perm = next(p for p in permissions if p["action"] == "view")

    role = client.post("/roles", headers=headers, json={"name": "Temp Role", "permission_ids": [view_perm["id"]]}).json()
    client.post("/users", headers=headers, json={"full_name": "Temp User", "email": "temp.user@demo-water.dev", "role_id": role["id"]})

    resp = client.delete(f"/roles/{role['id']}", headers=headers)
    assert resp.status_code == 400
    assert "Reassign" in resp.json()["detail"]
