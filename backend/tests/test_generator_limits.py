"""Limit meczów dziennie z generatora i globalny przyjazd przed meczem (ustawienia)."""

DAY = {"date_from": "2026-10-10", "date_to": "2026-10-10"}


def _setup(client, n_matches: int):
    venue = client.post(
        "/api/venues", json={"name": "Stadion", "city": "Warszawa", "latitude": 52.19, "longitude": 20.88}
    ).json()
    ref = client.post(
        "/api/referees",
        json={"first_name": "Jan", "last_name": "Kowalski", "city": "Warszawa", "latitude": 52.19, "longitude": 20.88,
              "preferred_matches_per_day": 5, "max_matches_per_day": 6, "max_matches_per_weekend": 10,
              "preferred_matches_per_weekend": 6},
    ).json()
    client.post("/api/availability", json={"referee_id": ref["id"], "date": "2026-10-10"})
    for i in range(n_matches):
        client.post("/api/matches", json={
            "date": "2026-10-10", "start_time": f"{8 + 3 * i:02d}:00", "estimated_end_time": f"{9 + 3 * i:02d}:30",
            "home_team": f"Gospodarz {i}", "away_team": f"Gość {i}", "venue_id": venue["id"],
        })
    return ref


def _update_settings(client, **changes):
    s = client.get("/api/settings").json()
    assert client.put("/api/settings", json={**s, **changes}).status_code == 200


def test_generator_assigns_at_most_three_matches_per_day(client):
    ref = _setup(client, 5)
    preview = client.post("/api/optimization/generate", json=DAY).json()
    assert len(preview["assignments"]) == 3
    assert len(preview["unassigned"]) == 2

    # Admin może ręcznie dobrać czwarty mecz — limit 3 dotyczy tylko automatu.
    client.post("/api/optimization/confirm", json={"run_id": preview["run_id"]})
    match_id = preview["unassigned"][0]["match"]["match_id"]
    cand = client.get("/api/assignments/candidates", params={"match_id": match_id}).json()
    assert next(c for c in cand if c["referee_id"] == ref["id"])["feasible"]
    r = client.post("/api/assignments", json={"match_id": match_id, "referee_id": ref["id"]}).json()
    assert r["warning"] is None


def test_daily_cap_is_configurable(client):
    _setup(client, 5)
    _update_settings(client, generator_max_matches_per_day=4)
    assert len(client.post("/api/optimization/generate", json=DAY).json()["assignments"]) == 4


def test_arrival_before_match_is_a_global_setting(client):
    _setup(client, 1)  # mecz o 08:00
    _update_settings(client, arrival_before_minutes=90)
    preview = client.post("/api/optimization/generate", json=DAY).json()
    reasons = " ".join(preview["assignments"][0]["explanation"]["reasons"])
    assert "06:30" in reasons
    m = client.get("/api/matches", params=DAY).json()[0]
    assert "arrival_before_minutes" not in m
