def test_login_success(client, seed_password):
    resp = client.post("/auth/login", json={"email": "utilityadmin@demo-water.dev", "password": seed_password})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_wrong_password(client, seed_password):
    resp = client.post("/auth/login", json={"email": "utilityadmin@demo-water.dev", "password": "wrong"})
    assert resp.status_code == 401


def test_me_requires_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_profile_and_roles(client, seed_password):
    login = client.post("/auth/login", json={"email": "csr@demo-water.dev", "password": seed_password})
    token = login.json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "csr@demo-water.dev"
    assert any(r["name"] == "CSR" for r in body["roles"])
    assert body["tenant_id"] is not None
    # CSR only has consumer+reports module access -- drives the frontend nav.
    assert set(body["permission_modules"]) == {"consumer", "reports"}


def test_me_permission_modules_empty_for_superadmin(client, seed_password):
    login = client.post("/auth/login", json={"email": "superadmin@utilityos.dev", "password": seed_password})
    token = login.json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()["permission_modules"] == []


def test_refresh_token_flow(client, seed_password):
    login = client.post("/auth/login", json={"email": "csr@demo-water.dev", "password": seed_password})
    refresh_token = login.json()["refresh_token"]
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_refresh_rejects_access_token(client, seed_password):
    login = client.post("/auth/login", json={"email": "csr@demo-water.dev", "password": seed_password})
    access_token = login.json()["access_token"]
    resp = client.post("/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401
