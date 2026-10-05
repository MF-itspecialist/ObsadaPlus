"""Import eksportu terminarza Łączy Nas Piłka (plik z tools/lnp-export.js)."""

import datetime as dt
import json

import pytest

from app.importers.json_importer import ImportFormatError
from app.importers.lnp_importer import LNPMatchImporter, iter_raw_matches

TODAY = dt.date(2026, 10, 5)


def _match(id_, when, host, guest, **kw):
    return {"id": id_, "dateTime": when, "host": {"id": f"h{id_}", "name": host}, "guest": {"id": f"g{id_}", "name": guest}, **kw}


def _export(*competitions):
    return {"source": "laczynaspilka.pl", "exportedAt": "2026-10-05T10:00:00Z", "competitions": list(competitions)}


def _comp(league, matches, play=None, group="Rozgrywki ZPN"):
    return {"leagueGroup": {"id": "g", "name": group}, "league": {"id": "l", "name": league},
            "play": play and {"id": "p", "name": play}, "matches": matches}


def _records(data):
    importer = LNPMatchImporter(json.dumps(data), date_from=TODAY)
    return importer.fetch_matches(), importer.warnings


def test_parses_upcoming_matches_with_levels_and_venues():
    data = _export(
        _comp("IV liga", [  # kolejki z zagnieżdżoną listą meczów
            {"queue": 10, "matches": [
                _match(1, "2026-10-11T13:00:00Z", "KS Ursus", "Legionovia", stadium={"facilityName": "Stadion KS Ursus", "cityName": "Warszawa"}),
                _match(2, "2026-09-27T15:00:00", "Znicz II", "Pilica", score="2:1"),  # już rozegrany
            ]},
        ], play="grupa I"),
        _comp("Junior młodszy B1", [_match(3, "2026-10-10T11:00:00", "Escola Varsovia", "Ursus", stadiumName="Boisko Escola")], play="Junior młodszy B1"),
        _comp("Orlik E1", [_match(4, "2026-10-10T09:00:00", "A", "B")]),  # poniżej D2 — pomijamy
    )
    records, warnings = _records(data)
    assert [r.external_id for r in records] == ["lnp:3", "lnp:1"]
    junior, senior = records
    assert senior.date == dt.date(2026, 10, 11) and senior.start_time == dt.time(15, 0)  # 13:00 UTC = 15:00 w Polsce
    assert senior.league == "IV liga – grupa I" and senior.required_referees == 3
    assert (senior.venue_name, senior.venue_city) == ("Stadion KS Ursus", "Warszawa")
    assert junior.league == "Junior młodszy B1" and junior.required_referees == 1
    assert junior.venue_name == "Boisko Escola"
    assert warnings == []


def test_falls_back_to_home_ground_and_skips_unknown_time_and_cancelled():
    data = _export(_comp("Klasa A", [
        _match(1, "2026-10-12T14:00:00", "KS Wesoła", "Marcovia II"),
        _match(2, "2026-10-12T00:00:00", "Mazur", "Delta"),
        _match(3, "2026-10-12T16:00:00", "Wilga", "Pogoń", stateTranslation="Odwołany"),
    ]))
    records, warnings = _records(data)
    assert len(records) == 1 and records[0].venue_name == "KS Wesoła" and records[0].required_referees == 1
    assert warnings == ["Pominięto 1 meczów bez ustalonej godziny rozpoczęcia"]


def test_iter_raw_matches_handles_team_names_in_nested_objects():
    raw = {"items": [{"round": 1, "rows": [{"id": 9, "dateTime": "2026-10-11T12:00:00", "host": {"team": {"name": "A"}}, "guest": "B"}]}]}
    assert [m["id"] for m in iter_raw_matches(raw)] == [9]


def test_rejects_non_lnp_file():
    with pytest.raises(ImportFormatError):
        LNPMatchImporter(json.dumps([{"home_team": "A"}])).fetch_matches()


def test_upload_endpoint_detects_lnp_export_and_reports_unknown_venues(client):
    client.post("/api/venues", json={"name": "Stadion KS Ursus", "city": "Warszawa", "latitude": 52.19, "longitude": 20.88})
    future = (dt.date.today() + dt.timedelta(days=7)).isoformat()
    data = _export(_comp("Klasa okręgowa", [
        _match(1, f"{future}T15:00:00", "KS Ursus", "Legionovia", stadiumName="Stadion KS Ursus"),
        _match(2, f"{future}T11:00:00", "Mazur", "Delta"),
        _match(3, f"{future}T13:00:00", "Mazur II", "Delta II", stadiumName="Mazur"),
    ]))
    files = {"file": ("lnp-terminarz.json", json.dumps(data), "application/json")}
    result = client.post("/api/matches/import", files=files).json()
    assert result["created"] == 1 and result["updated"] == 0
    assert result["errors"] == ["Nieznany obiekt 'Mazur' (2 mecz.): dodaj go w zakładce Obiekty i zaimportuj plik ponownie"]
    match = client.get("/api/matches").json()[0]
    assert match["external_id"] == "lnp:1" and match["required_referees"] == 3
    # ponowny import aktualizuje zamiast dublować
    assert client.post("/api/matches/import", files=files).json()["updated"] == 1
