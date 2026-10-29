"""Panel sędziego: opublikowane mecze i samodzielne zgłaszanie dyspozycyjności."""

import datetime as dt

import pytest

from app.services import referee_panel_service

PERIOD = {"date_from": "2026-10-09", "date_to": "2026-10-12"}
TODAY = dt.date(2026, 10, 8)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(referee_panel_service, "today", lambda: TODAY)


def _login(c, login, password):
    c.post("/api/auth/logout")
    assert c.post("/api/auth/login", json={"login": login, "password": password}).status_code == 200


def _referee_login(c, referee_id, login="sedzia"):
    """Zakłada konto sędziego (jako obsadzający), loguje się na nie i zwraca hasło."""
    password = c.post("/api/users", json={"login": login, "role": "REFEREE", "referee_id": referee_id}).json()["password"]
    _login(c, login, password)
    return password


def _admin_login(c):
    from tests.conftest import ADMIN_LOGIN, ADMIN_PASSWORD

    _login(c, ADMIN_LOGIN, ADMIN_PASSWORD)


def test_referee_sees_only_published_own_matches(seeded_client):
    c = seeded_client
    preview = c.post("/api/optimization/generate", json=PERIOD).json()
    c.post("/api/optimization/confirm", json={"run_id": preview["run_id"]})
    a = c.get("/api/assignments", params=PERIOD).json()[0]
    referee_id = a["referee_id"]
    own = [x for x in c.get("/api/assignments", params=PERIOD).json() if x["referee_id"] == referee_id]

    pw = _referee_login(c, referee_id)
    assert c.get("/api/me/matches").json() == [], "przed publikacją sędzia nic nie widzi"
    assert c.get("/api/referees").status_code == 403

    _admin_login(c)
    c.post("/api/publications", json=PERIOD)
    _login(c, "sedzia", pw)

    matches = c.get("/api/me/matches").json()
    assert {m["match_id"] for m in matches} == {x["match_id"] for x in own}
    m = matches[0]
    assert m["role_label"] and m["venue_name"] and m["version"] == 1
    assert all(x["referee_name"] != a["referee_name"] for x in m["crew"])

    # nowa wersja bez tego sędziego — mecz znika z panelu
    _admin_login(c)
    c.delete(f"/api/assignments/{a['id']}")
    c.post("/api/publications", json=PERIOD)
    _login(c, "sedzia", pw)
    assert a["match_id"] not in {m["match_id"] for m in c.get("/api/me/matches").json()}


def test_referee_declares_own_availability(client):
    ref = client.post(
        "/api/referees",
        json={"first_name": "Jan", "last_name": "Kowalski", "city": "Warszawa", "address": "Ursynów",
              "latitude": 52.15, "longitude": 21.03},
    ).json()
    _referee_login(client, ref["id"])
    c = client
    r = c.put("/api/me/availability", json={"items": [
        {"date": "2026-10-10", "available": True},
        {"date": "2026-10-11", "available": True, "available_from": "12:00", "available_to": "18:00"},
        {"date": "2026-10-12", "available": False},
    ]})
    assert r.status_code == 200, r.text
    assert all(x["declared_by_referee"] for x in r.json())

    # przeszłość i dziś są zamknięte, zbyt odległa przyszłość też
    assert c.put("/api/me/availability", json={"items": [{"date": "2026-10-08"}]}).status_code == 422
    assert c.put("/api/me/availability", json={"items": [{"date": "2027-06-01"}]}).status_code == 422
    bad = {"date": "2026-10-17", "available_from": "18:00", "available_to": "12:00"}
    assert c.put("/api/me/availability", json={"items": [bad]}).status_code == 422

    assert c.put("/api/me/availability", json={"cleared": ["2026-10-12"]}).status_code == 200
    own = c.get("/api/me/availability", params=PERIOD).json()
    assert [x["date"] for x in own] == ["2026-10-10", "2026-10-11"]

    # obsadzający widzi zgłoszenie; jego zmiana wartości zdejmuje znacznik, zapis bez zmian go zostawia
    _admin_login(c)
    rows = {x["date"]: x for x in c.get("/api/availability", params=PERIOD).json()}
    assert rows["2026-10-10"]["declared_by_referee"] is True
    c.post("/api/availability/bulk", json={"items": [
        {"referee_id": ref["id"], "date": "2026-10-10", "available": True},
        {"referee_id": ref["id"], "date": "2026-10-11", "available": False},
    ]})
    rows = {x["date"]: x for x in c.get("/api/availability", params=PERIOD).json()}
    assert rows["2026-10-10"]["declared_by_referee"] is True
    assert rows["2026-10-11"]["declared_by_referee"] is False


def test_admin_has_no_referee_panel(client):
    assert client.get("/api/me/matches").status_code == 403
