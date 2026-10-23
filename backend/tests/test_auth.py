"""Logowanie, role i zarządzanie kontami."""

from tests.conftest import ADMIN_LOGIN, ADMIN_PASSWORD

PERIOD = {"date_from": "2026-10-09", "date_to": "2026-10-12"}


def _login(c, login, password):
    return c.post("/api/auth/login", json={"login": login, "password": password})


def test_api_requires_login(anon_client):
    c = anon_client
    assert c.get("/api/health").status_code == 200
    assert c.get("/api/referees").status_code == 401
    assert c.get("/api/assignments/export.pdf", params=PERIOD).status_code == 401
    assert c.get("/api/auth/me").status_code == 401


def test_login_logout_and_cookie(anon_client):
    c = anon_client
    assert _login(c, ADMIN_LOGIN, "zle-haslo").status_code == 401
    r = _login(c, "  ADMIN ", ADMIN_PASSWORD)  # login bez względu na wielkość liter i spacje
    assert r.status_code == 200
    cookie = r.headers["set-cookie"]
    assert "obsada_session=" in cookie and "HttpOnly" in cookie and "samesite=lax" in cookie.lower()
    assert c.get("/api/auth/me").json()["role"] == "ADMIN"
    assert c.get("/api/referees").status_code == 200
    assert c.post("/api/auth/logout").status_code == 204
    assert c.get("/api/referees").status_code == 401


def test_login_is_blocked_after_repeated_failures(anon_client):
    c = anon_client
    for _ in range(5):
        assert _login(c, ADMIN_LOGIN, "zle").status_code == 401
    r = _login(c, ADMIN_LOGIN, ADMIN_PASSWORD)
    assert r.status_code == 401 and "Za dużo" in r.json()["detail"]


def test_referee_account_has_no_access_to_admin_api(client):
    referee = client.post(
        "/api/referees",
        json={"first_name": "Jan", "last_name": "Kowalski", "city": "Warszawa", "address": "Ursynów",
              "latitude": 52.15, "longitude": 21.03},
    ).json()
    # konto sędziego musi wskazywać sędziego
    assert client.post("/api/users", json={"login": "jan", "role": "REFEREE"}).status_code == 422
    created = client.post("/api/users", json={"login": "Jan.K", "role": "REFEREE", "referee_id": referee["id"]}).json()
    password = created["password"]
    assert len(password) == 12
    assert created["user"]["login"] == "jan.k"
    assert created["user"]["referee_name"] == "Jan Kowalski"
    # drugi login dla tego samego sędziego jest odrzucany
    r = client.post("/api/users", json={"login": "jan2", "role": "REFEREE", "referee_id": referee["id"]})
    assert r.status_code == 422

    client.post("/api/auth/logout")
    assert _login(client, "jan.k", password).status_code == 200
    assert client.get("/api/auth/me").json()["role"] == "REFEREE"
    assert client.get("/api/referees").status_code == 403
    assert client.get("/api/users").status_code == 403


def test_password_change_and_reset(client):
    r = client.post("/api/auth/password", json={"current_password": "zle", "new_password": "nowe-haslo-1"})
    assert r.status_code == 422
    r = client.post("/api/auth/password", json={"current_password": ADMIN_PASSWORD, "new_password": "krotkie"})
    assert r.status_code == 422
    r = client.post("/api/auth/password", json={"current_password": ADMIN_PASSWORD, "new_password": "nowe-haslo-1"})
    assert r.status_code == 204
    assert client.get("/api/auth/me").status_code == 200  # ta przeglądarka zostaje zalogowana

    other = client.post("/api/users", json={"login": "drugi", "role": "ADMIN", "password": "haslo-drugie"}).json()
    assert other["password"] is None
    reset = client.post(f"/api/users/{other['user']['id']}/reset-password").json()
    client.post("/api/auth/logout")
    assert _login(client, "drugi", "haslo-drugie").status_code == 401
    assert _login(client, "drugi", reset["password"]).status_code == 200


def test_admin_cannot_lock_themselves_out(client):
    me = client.get("/api/auth/me").json()
    r = client.put(f"/api/users/{me['id']}", json={"role": "ADMIN", "active": False})
    assert r.status_code == 422
    assert client.delete(f"/api/users/{me['id']}").status_code == 422


def test_deactivated_user_is_logged_out(client):
    other = client.post("/api/users", json={"login": "drugi", "role": "ADMIN", "password": "haslo-drugie"}).json()
    uid = other["user"]["id"]
    assert client.put(f"/api/users/{uid}", json={"role": "ADMIN", "active": False}).json()["active"] is False
    client.post("/api/auth/logout")
    assert _login(client, "drugi", "haslo-drugie").status_code == 401


def test_first_admin_from_environment(db_session, monkeypatch):
    from app.config import get_config
    from app.services import auth_service

    monkeypatch.setenv("ADMIN_PASSWORD", "start-haslo-99")
    get_config.cache_clear()
    try:
        with db_session() as db:
            user = auth_service.ensure_admin(db)
            assert user is not None and user.login == "admin" and user.role.value == "ADMIN"
            assert auth_service.ensure_admin(db) is None  # tylko gdy nie ma żadnego konta
    finally:
        get_config.cache_clear()
