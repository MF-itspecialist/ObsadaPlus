"""Automatyczna aktualizacja meczów: harmonogram, historia importów, zmiany obsadzonych meczów."""

import datetime as dt
import time

from app.importers.base import MatchImporter, MatchImportRecord
from app.models import ImportRun
from app.services import auto_import_service as ai

WARSAW = ai.WARSAW


class FakeImporter(MatchImporter):
    def __init__(self, records):
        self.records = records
        self.warnings = []

    def fetch_matches(self):
        return self.records


def _record(start="12:00", day=dt.date(2027, 3, 13), venue="Stadion Testowy"):
    return MatchImportRecord(
        external_id="90minut:1:ab", date=day, start_time=dt.time.fromisoformat(start), league="IV liga",
        home_team="Agape Białołęka", away_team="KS Ursus", venue_name=venue, venue_city="Warszawa",
        venue_latitude=52.3, venue_longitude=21.0, required_referees=1,
    )


def test_change_of_assigned_match_is_reported(client, db_session):
    first = ai.run_import(db_session, "manual", lambda db, today: FakeImporter([_record()]))
    m = client.get("/api/matches", params={"date_from": "2027-03-13", "date_to": "2027-03-13"}).json()[0]
    ref = client.post("/api/referees", json={"first_name": "Jan", "last_name": "Test", "city": "Warszawa",
                                              "latitude": 52.2, "longitude": 21.0}).json()
    client.post("/api/assignments", json={"match_id": m["id"], "referee_id": ref["id"]})

    second = ai.run_import(db_session, "auto", lambda db, today: FakeImporter([_record(start="15:30")]))
    runs = client.get("/api/imports").json()
    assert [r["id"] for r in runs] == [second, first]
    assert runs[0]["trigger"] == "auto" and runs[0]["status"] == "ok" and runs[0]["updated"] == 1
    [change] = runs[0]["changes"]
    assert change["match_id"] == m["id"] and change["what"] == "godzina 12:00 → 15:30"
    assert change["referees"] == ["Jan Test"]
    assert runs[1]["changes"] == []


def test_failed_import_is_recorded(db_session):
    def boom(db, today):
        raise RuntimeError("90minut.pl nie odpowiada")

    run_id = ai.run_import(db_session, "auto", boom)
    with db_session() as db:
        run = db.get(ImportRun, run_id)
        assert run.status == "error" and "nie odpowiada" in run.messages[0]


def test_auto_run_due_once_a_day_after_hour(db_session):
    at = lambda h: dt.datetime(2026, 10, 29, h, 0, tzinfo=WARSAW)  # noqa: E731
    with db_session() as db:
        assert not ai.auto_run_due(db, at(2))
        assert ai.auto_run_due(db, at(3))
        assert ai.auto_run_due(db, at(9))  # restart po godzinie — nadrabia
        # import automatyczny z tego dnia (03:05 czasu polskiego = 02:05 UTC)
        db.add(ImportRun(source="x", trigger="auto", status="ok", started_at=dt.datetime(2026, 10, 29, 2, 5), changes=[], messages=[]))
        db.commit()
        assert not ai.auto_run_due(db, at(9))
        assert ai.auto_run_due(db, dt.datetime(2026, 10, 30, 3, 0, tzinfo=WARSAW))


def test_disabled_in_settings(client, db_session):
    s = client.get("/api/settings").json()
    client.put("/api/settings", json={**s, "auto_import_enabled": False})
    with db_session() as db:
        assert not ai.auto_run_due(db, dt.datetime(2026, 10, 29, 12, tzinfo=WARSAW))


def test_run_now_endpoint_runs_in_background(client, monkeypatch):
    monkeypatch.setattr(ai, "default_importer", lambda db, today: FakeImporter([_record()]))
    r = client.post("/api/imports/run")
    assert r.status_code == 202
    for _ in range(50):
        run = client.get("/api/imports").json()[0]
        if run["status"] != "running":
            break
        time.sleep(0.05)
    assert run["id"] == r.json()["run_id"] and run["status"] == "ok" and run["created"] == 1
