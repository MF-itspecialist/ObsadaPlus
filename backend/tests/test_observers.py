"""Obserwatorzy: rola O na meczach wybranych lig albo zaznaczonych ręcznie."""

DAY = "2027-03-13"
PERIOD = {"date_from": DAY, "date_to": DAY}
BODY = {"city": "Warszawa", "latitude": 52.19, "longitude": 20.88}


def _setup(client):
    venue = client.post("/api/venues", json={"name": "Stadion", "city": "Warszawa", "latitude": 52.19, "longitude": 20.88}).json()
    refs = {}
    for name, lic in [("Główny", ["Sędzia IV liga"]), ("Asystent1", ["Asystent III/IV/V liga (w tym asystenci mazowieccy)"]),
                      ("Asystent2", ["Asystent III/IV/V liga (w tym asystenci mazowieccy)"]), ("Obserwujący", ["Obserwator"])]:
        r = client.post("/api/referees", json={**BODY, "first_name": "Jan", "last_name": name, "licenses": lic}).json()
        client.post("/api/availability", json={"referee_id": r["id"], "date": DAY})
        refs[name] = r["id"]

    def match(league, **kw):
        return client.post("/api/matches", json={"date": DAY, "start_time": "12:00", "estimated_end_time": "13:45", "league": league,
                                                 "home_team": "A", "away_team": "B", "venue_id": venue["id"], **kw}).json()

    return refs, match


def _levels(client, levels):
    s = client.get("/api/settings").json()
    return client.put("/api/settings", json={**s, "observer_levels": levels})


def test_observer_levels_drive_matches_and_generator(client):
    refs, match = _setup(client)
    iv = match("IV liga", required_referees=3)
    klasa_a = match("Klasa A")
    assert not iv["observer_required"]

    assert _levels(client, ["IV liga"]).status_code == 200
    by_id = {m["id"]: m for m in client.get("/api/matches", params=PERIOD).json()}
    assert by_id[iv["id"]]["observer_required"] and not by_id[klasa_a["id"]]["observer_required"]

    preview = client.post("/api/optimization/generate", json=PERIOD).json()
    roles = {(a["match"]["match_id"], a["role"]): a["referee_id"] for a in preview["assignments"]}
    assert roles[(iv["id"], "OBSERVER")] == refs["Obserwujący"]
    assert roles[(iv["id"], "MAIN")] == refs["Główny"]
    # obserwator jedzie sam — bez wspólnego dojazdu zespołu
    obs = next(a for a in preview["assignments"] if a["role"] == "OBSERVER")
    assert not any("wspólny dojazd" in r for r in obs["explanation"]["reasons"])
    # Klasa A bez obserwatora: obserwator nie sędziuje
    assert (klasa_a["id"], "MAIN") not in roles

    assert _levels(client, ["Liga mistrzów"]).status_code == 422


def test_manual_observer_survives_settings_and_removal_clears_assignment(client):
    refs, match = _setup(client)
    m = match("Klasa A", observer_required=True)
    assert m["observer_required"] and m["observer_manual"]
    _levels(client, [])
    assert client.get(f"/api/matches/{m['id']}").json()["observer_required"]

    r = client.post("/api/assignments", json={"match_id": m["id"], "referee_id": refs["Obserwujący"], "role": "OBSERVER"})
    assert r.status_code in (200, 201), r.text
    body = {k: m[k] for k in ("date", "start_time", "estimated_end_time", "league", "home_team", "away_team", "venue_id", "required_referees")}
    updated = client.put(f"/api/matches/{m['id']}", json={**body, "observer_required": False}).json()
    assert not updated["observer_required"]
    assert [a for a in updated["assignments"] if a["role"] == "OBSERVER"] == []


def test_new_match_follows_levels_unless_set(client):
    _, match = _setup(client)
    _levels(client, ["IV liga"])
    auto = match("IV liga")
    assert auto["observer_required"] and not auto["observer_manual"]
    off = match("IV liga", observer_required=False)
    assert not off["observer_required"] and off["observer_manual"]
