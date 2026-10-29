"""Powiadomienia e-mail: po publikacji, przypomnienie o dyspozycyjności, skrzynka nadawcza."""

import datetime as dt

import pytest

from app.models import OutboxMessage
from app.services import notification_service as ns

PERIOD = {"date_from": "2026-10-09", "date_to": "2026-10-12"}
WARSAW = dt.timezone(dt.timedelta(hours=2))


@pytest.fixture()
def outbox(monkeypatch):
    """Skrzynka „skonfigurowana”, wysyłka do listy zamiast SMTP."""
    sent = []
    monkeypatch.setattr(ns, "smtp_configured", lambda: True)
    monkeypatch.setattr(ns, "SENDER", lambda m: sent.append((m.to_email, m.subject, m.body)))
    return sent


def _emails(c, ids):
    for rid in ids:
        r = c.get(f"/api/referees/{rid}").json()
        body = {k: v for k, v in r.items() if k not in ("id", "location_label", "region", "license_class", "license_class_rank")}
        assert c.put(f"/api/referees/{rid}", json={**body, "email": f"s{rid}@example.com"}).status_code == 200


def _published(c):
    preview = c.post("/api/optimization/generate", json=PERIOD).json()
    c.post("/api/optimization/confirm", json={"run_id": preview["run_id"]})
    return c.get("/api/assignments", params=PERIOD).json()


def test_publication_mails_each_referee_then_only_changes(seeded_client, db_session):
    c = seeded_client
    assignments = _published(c)
    ids = sorted({a["referee_id"] for a in assignments})
    _emails(c, ids[1:])  # pierwszy bez adresu

    r = c.post("/api/publications", json=PERIOD).json()
    assert r["notifications"]["queued"] == len(ids) - 1
    assert len(r["notifications"]["without_email"]) == 1

    ns.send_pending(db_session)  # bez skrzynki: nic nie wychodzi
    msgs = c.get("/api/notifications").json()
    assert {m["status"] for m in msgs} == {"pending"}
    m = next(m for m in msgs if m["referee_id"] == ids[1])
    assert m["subject"].startswith("Obsada sędziowska 09.10")
    assert "Twoja rola:" in m["body"]

    # druga publikacja bez zmian — żadnych nowych wiadomości
    assert c.post("/api/publications", json=PERIOD).json()["notifications"]["queued"] == 0

    # zdjęcie jednego sędziego z meczu → mail tylko do niego (i ewentualnie zespołu tego meczu)
    a = next(a for a in assignments if a["referee_id"] == ids[1])
    c.delete(f"/api/assignments/{a['id']}")
    r = c.post("/api/publications", json=PERIOD).json()
    assert r["notifications"]["queued"] >= 1
    changed = [m for m in c.get("/api/notifications").json() if m["subject"].startswith("Zmiana obsady")]
    mine = next(m for m in changed if m["referee_id"] == ids[1])
    assert "Nie sędziujesz już:" in mine["body"]


def test_send_pending_and_test_mail(client, db_session, outbox):
    r = client.post("/api/notifications/test", json={"to": "obsada@example.com"}).json()
    assert r["status"] == "sent" and outbox[0][0] == "obsada@example.com"
    assert client.post("/api/notifications/test", json={"to": "zly-adres"}).status_code == 422

    with db_session() as db:
        db.add(OutboxMessage(to_email="a@example.com", to_name="A", kind="publication", topic="", subject="S", body="B", status="pending", error=""))
        db.commit()
    assert client.post("/api/notifications/send-pending").json() == {"sent": 1, "failed": 0}
    st = client.get("/api/notifications/status").json()
    assert st["smtp_configured"] and st["pending"] == 0


def test_send_pending_without_mailbox_is_refused(client):
    assert client.post("/api/notifications/send-pending").status_code == 409


def test_failed_send_is_kept_with_error(client, db_session, monkeypatch):
    monkeypatch.setattr(ns, "smtp_configured", lambda: True)

    def boom(m):
        raise OSError("serwer odrzucił logowanie")

    monkeypatch.setattr(ns, "SENDER", boom)
    r = client.post("/api/notifications/test", json={"to": "obsada@example.com"}).json()
    assert r["status"] == "failed" and "odrzucił" in r["error"]


def test_availability_reminder_once_per_weekend(client, db_session, outbox):
    body = {"city": "Warszawa", "latitude": 52.2, "longitude": 21.0}
    a = client.post("/api/referees", json={**body, "first_name": "Ala", "last_name": "Zgłoszona", "email": "a@example.com"}).json()
    client.post("/api/referees", json={**body, "first_name": "Bob", "last_name": "Spóźniony", "email": "b@example.com"})
    client.post("/api/referees", json={**body, "first_name": "Cez", "last_name": "Bezadresu"})
    client.post("/api/availability", json={"referee_id": a["id"], "date": "2026-11-07"})

    tue_morning = dt.datetime(2026, 11, 3, 9, 0, tzinfo=WARSAW)
    tue_evening = dt.datetime(2026, 11, 3, 18, 30, tzinfo=WARSAW)
    friday = dt.datetime(2026, 11, 6, 18, 30, tzinfo=WARSAW)
    assert ns.upcoming_weekend(dt.date(2026, 11, 3)) == [dt.date(2026, 11, d) for d in (6, 7, 8, 9)]
    assert ns.reminder_tick(db_session, tue_morning) == 0
    assert ns.reminder_tick(db_session, friday) == 0  # po czwartku już nie
    assert ns.reminder_tick(db_session, tue_evening) == 1
    assert [o[0] for o in outbox] == ["b@example.com"]
    assert "06.11–09.11.2026" in outbox[0][1]
    assert ns.reminder_tick(db_session, tue_evening + dt.timedelta(days=1)) == 0  # raz na weekend


def test_referee_sets_own_contact(seeded_client):
    c = seeded_client
    rid = c.get("/api/referees").json()[0]["id"]
    pw = c.post("/api/users", json={"login": "sedzia", "role": "REFEREE", "referee_id": rid}).json()["password"]
    c.post("/api/auth/logout")
    c.post("/api/auth/login", json={"login": "sedzia", "password": pw})
    assert c.put("/api/me/contact", json={"email": "zly"}).status_code == 422
    assert c.put("/api/me/contact", json={"email": " jan@example.com ", "notify_email": True}).json()["email"] == "jan@example.com"
    assert c.get("/api/me/contact").json() == {"email": "jan@example.com", "notify_email": True}
