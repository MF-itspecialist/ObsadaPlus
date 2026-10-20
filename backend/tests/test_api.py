"""Testy integracyjne REST API (przepływ: dane → generowanie → podgląd → zatwierdzenie → korekta)."""

PERIOD = {"date_from": "2026-10-10", "date_to": "2026-10-11"}


def _venue(client, **kw):
    body = {"name": "Stadion KS Ursus", "city": "Warszawa", "address": "ul. Sosnkowskiego 3", "latitude": 52.19, "longitude": 20.88}
    return client.post("/api/venues", json={**body, **kw}).json()


def _referee(client, **kw):
    body = {
        "first_name": "Jan", "last_name": "Kowalski", "city": "Warszawa", "address": "Ursynów",
        "latitude": 52.15, "longitude": 21.03,
    }
    return client.post("/api/referees", json={**body, **kw}).json()


def test_referee_crud(client):
    ref = _referee(client)
    assert ref["id"] and ref["max_matches_per_day"] == 3
    ref["city"] = "Piaseczno"
    assert client.put(f"/api/referees/{ref['id']}", json=ref).json()["city"] == "Piaseczno"
    assert len(client.get("/api/referees").json()) == 1
    assert client.delete(f"/api/referees/{ref['id']}").status_code == 204
    assert client.get(f"/api/referees/{ref['id']}").status_code == 404


def test_referee_validation(client):
    r = client.post(
        "/api/referees",
        json={"first_name": "A", "last_name": "B", "latitude": 52, "longitude": 21,
              "preferred_matches_per_day": 4, "max_matches_per_day": 3},
    )
    assert r.status_code == 422


def test_match_crud_and_validation(client):
    venue = _venue(client)
    body = {
        "date": "2026-10-10", "start_time": "14:00", "estimated_end_time": "15:45", "league": "U17",
        "home_team": "Escola Varsovia", "away_team": "Ursus Warszawa", "venue_id": venue["id"],
    }
    m = client.post("/api/matches", json=body).json()
    assert m["status"] == "UNASSIGNED" and m["venue"]["name"] == "Stadion KS Ursus"
    bad = client.post("/api/matches", json={**body, "estimated_end_time": "13:00"})
    assert bad.status_code == 422
    assert client.put(f"/api/matches/{m['id']}", json={**body, "league": "U19"}).json()["league"] == "U19"
    assert len(client.get("/api/matches", params=PERIOD).json()) == 1


def test_availability_upsert(client):
    ref = _referee(client)
    entry = {"referee_id": ref["id"], "date": "2026-10-10", "available_from": "08:00", "available_to": "18:00"}
    first = client.post("/api/availability", json=entry).json()
    second = client.post("/api/availability", json={**entry, "available": False}).json()
    assert first["id"] == second["id"] and second["available"] is False and second["available_from"] is None
    assert len(client.get("/api/availability", params={"referee_id": ref["id"]}).json()) == 1


def test_generate_preview_does_not_save_until_confirm(seeded_client):
    c = seeded_client
    preview = c.post("/api/optimization/generate", json=PERIOD).json()
    stats = preview["stats"]
    assert stats["matches_total"] == 20
    assert stats["matches_assigned"] + stats["matches_unassigned"] == 20
    assert preview["unassigned"], "dane testowe zawierają mecz bez możliwej obsady"
    assert preview["unassigned"][0]["reasons"]
    assert c.get("/api/assignments", params=PERIOD).json() == []

    confirmed = c.post("/api/optimization/confirm", json={"run_id": preview["run_id"]}).json()
    assert confirmed["saved_assignments"] == stats["slots_assigned"]
    assert len(c.get("/api/assignments", params=PERIOD).json()) == stats["slots_assigned"]
    # drugi raz tego samego podglądu nie można zatwierdzić
    assert c.post("/api/optimization/confirm", json={"run_id": preview["run_id"]}).status_code == 409

    dash = c.get("/api/dashboard", params=PERIOD).json()
    assert dash["matches_assigned"] == stats["matches_assigned"]
    assert dash["total_distance_km"] > 0


def test_manual_assignment_survives_regeneration_unless_full(seeded_client):
    c = seeded_client
    preview = c.post("/api/optimization/generate", json=PERIOD).json()
    c.post("/api/optimization/confirm", json={"run_id": preview["run_id"]})
    board = c.get("/api/assignments/board", params=PERIOD).json()
    item = next(b for b in board if b["assignments"])
    current = item["assignments"][0]

    candidates = c.get("/api/assignments/candidates", params={"match_id": item["match_id"]}).json()
    other = next(x for x in candidates if x["feasible"] and x["referee_id"] != current["referee_id"])
    changed = c.put(f"/api/assignments/{current['id']}", json={"referee_id": other["referee_id"]}).json()
    assert changed["assignment"]["manually_modified"] is True
    assert changed["warning"] is None

    regen = c.post("/api/optimization/generate", json=PERIOD).json()
    kept = [a for a in regen["assignments"] if a["match"]["match_id"] == item["match_id"]]
    assert kept[0]["referee_id"] == other["referee_id"] and kept[0]["manually_modified"]
    c.post("/api/optimization/confirm", json={"run_id": regen["run_id"]})
    after = c.get("/api/assignments", params={"match_id": item["match_id"]}).json()
    assert after[0]["referee_id"] == other["referee_id"]

    full = c.post("/api/optimization/generate", json={**PERIOD, "mode": "FULL"}).json()
    regenerated = next(a for a in full["assignments"] if a["match"]["match_id"] == item["match_id"])
    assert regenerated["manually_modified"] is False


def test_manual_assignment_reports_conflict_warning(seeded_client):
    c = seeded_client
    matches = c.get("/api/matches", params=PERIOD).json()
    referees = c.get("/api/referees").json()
    inactive = next(r for r in referees if not r["active"])
    res = c.post("/api/assignments", json={"match_id": matches[0]["id"], "referee_id": inactive["id"]})
    assert res.status_code == 201
    assert res.json()["warning"] and "nieaktywny" in res.json()["warning"]
    board = c.get("/api/assignments/board", params=PERIOD).json()
    assert board[0]["assignments"][0]["conflict"]
    assert c.get("/api/dashboard", params=PERIOD).json()["conflicts"] == 1
    assert c.delete(f"/api/assignments/{res.json()['assignment']['id']}").status_code == 204
    assert c.get(f"/api/matches/{matches[0]['id']}").json()["status"] == "UNASSIGNED"


def test_import_json_and_csv(client):
    _venue(client)
    records = [{
        "external_id": "EXT-1", "date": "2026-10-10", "start_time": "12:00", "league": "U15",
        "home_team": "A", "away_team": "B", "venue_name": "stadion ks ursus",
    }]
    r = client.post("/api/matches/import/json", json=records).json()
    assert r == {"created": 1, "updated": 0, "errors": []}
    m = client.get("/api/matches").json()[0]
    assert m["estimated_end_time"] == "13:45:00"  # domyślne 105 min

    csv_body = (
        "external_id;date;start_time;estimated_end_time;home_team;away_team;venue_name;venue_latitude;venue_longitude\n"
        "EXT-1;2026-10-10;12:30;14:15;A;B;Stadion KS Ursus;;\n"
        "EXT-2;2026-10-11;10:00;11:45;C;D;Nowy Orlik;52.1;21.0\n"
    )
    r = client.post("/api/matches/import", files={"file": ("mecze.csv", csv_body, "text/csv")}).json()
    assert r == {"created": 1, "updated": 1, "errors": []}
    assert len(client.get("/api/venues").json()) == 2


def test_settings_roundtrip(client):
    s = client.get("/api/settings").json()
    assert s["transport_safety_buffer_minutes"] == 15
    s["transport_safety_buffer_minutes"] = 30
    assert client.put("/api/settings", json=s).json()["transport_safety_buffer_minutes"] == 30


def test_import_reuses_venue_with_polish_capitals(client):
    rec = {"date": "2026-10-10", "start_time": "12:00", "home_team": "A", "away_team": "B",
           "venue_name": "ŚLIMAK ARENA ŁOMIANKI", "venue_latitude": 52.33, "venue_longitude": 20.88}
    r = client.post("/api/matches/import/json", json=[{**rec, "external_id": "P-1"}, {**rec, "external_id": "P-2"}])
    assert r.json()["created"] == 2
    assert len(client.get("/api/venues").json()) == 1
