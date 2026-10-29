"""Uprawnienia licencji: poziom rozgrywek × rola (główny / asystent)."""

import pytest

from app.models.enums import RefereeRole
from app.optimization.licenses import LICENSE_RULES, Category, check_license, classify_league, license_catalog

MAIN, AS1 = RefereeRole.MAIN, RefereeRole.ASSISTANT_1


@pytest.mark.parametrize(
    "league,expected",
    [
        ("IV Liga", (Category.MEN, 6)),
        ("Piąta liga Grupa 2", (Category.MEN, 5)),
        ("Klasa okręgowa Grupa 1", (Category.MEN, 4)),
        ("Klasa A Grupa 3", (Category.MEN, 3)),
        ("Klasa B Grupa 7", (Category.MEN, 2)),
        ("I liga okręgowa C1 Trampkarz Grupa 1", (Category.MEN, 1)),
        ("A2 Junior \"Ekstraliga\"", (Category.MEN, 1)),
        ("U17", (Category.MEN, 1)),
        ("Czwarta liga kobiet", (Category.WOMEN, 1)),
        ("Ekstraliga kobiet", (Category.WOMEN, 4)),
        ("I liga futsal", (Category.FUTSAL, 2)),
        ("Puchar Polski", None),
        ("", None),
    ],
)
def test_classify_league(league, expected):
    assert classify_league(league) == expected


def test_klasa_b_referee_main_up_to_b_assistant_up_to_okregowa():
    lic = ["Sędzia klasa B"]
    assert check_license(lic, "Klasa B", MAIN) is None
    assert check_license(lic, "Klasa A", MAIN) == "licencja jako sędzia główny do: klasa B, mecz: klasa A"
    assert check_license(lic, "Klasa okręgowa", AS1) is None
    assert check_license(lic, "V liga", AS1) is not None


def test_mazovian_assistant_up_to_iv_liga_only_as_assistant():
    lic = ["Asystent III/IV/V liga (w tym asystenci mazowieccy)"]
    assert check_license(lic, "IV liga", AS1) is None
    assert check_license(lic, "III liga", AS1) is not None
    assert "nie uprawnia" in check_license(lic, "Klasa B", MAIN)


def test_district_assistant_up_to_okregowa():
    lic = ["Asystent okręgowy / pozostali"]
    assert check_license(lic, "Klasa okręgowa", RefereeRole.ASSISTANT_2) is None
    assert check_license(lic, "V liga", RefereeRole.ASSISTANT_2) is not None


@pytest.mark.parametrize("license", ["Sędzia IV liga", "Sędzia V liga", "Sędzia TopAmator A (w tym zawodowi)"])
def test_referee_above_okregowa_as_assistant_up_to_iii_liga(license):
    assert check_license([license], "III liga", AS1) is None
    assert check_license([license], "II liga", AS1) == "licencja jako asystent do: III liga, mecz: II liga"


def test_above_iii_liga_assistants_need_assistant_license():
    assert check_license(["Asystent s.c. (niezawodowy)"], "I liga", AS1) is None
    assert check_license(["Asystent s.c. (niezawodowy)"], "Ekstraklasa", AS1) is not None
    assert check_license(["Asystent zawodowy"], "Ekstraklasa", AS1) is None


def test_trial_referee_youth_only_as_main():
    lic = ["Sędzia próbny (C)"]
    assert check_license(lic, "D2 Młodzik Grupa 16", MAIN) is None
    assert check_license(lic, "Klasa B", MAIN) is not None
    assert check_license(lic, "Klasa okręgowa", AS1) is None


def test_best_license_wins_and_unknown_league_is_not_checked():
    assert check_license(["Sędzia klasa B", "Asystent III/IV/V liga (w tym asystenci mazowieccy)"], "IV liga", AS1) is None
    assert check_license([], "Puchar Polski", MAIN) is None
    assert check_license([], "Klasa B", MAIN).startswith("brak przydzielonej licencji")
    # obserwator: osobna licencja, niezależna od ligi; licencja sędziego nie wystarcza
    assert check_license(["Obserwator"], "IV liga", RefereeRole.OBSERVER) is None
    assert check_license(["Sędzia IV liga"], "Klasa B", RefereeRole.OBSERVER) == "brak uprawnień obserwatora"
    assert check_license(["Obserwator"], "Klasa B", MAIN) is not None


def test_women_referees_may_also_take_mens_matches():
    assert check_license(["Sędzia Ekstraliga kobiet"], "III liga", MAIN) is None
    assert check_license(["Sędzia Ekstraliga kobiet"], "II liga", MAIN) is not None
    assert check_license(["Sędzia I liga kobiet"], "Klasa okręgowa", MAIN) is None
    assert check_license(["Sędzia klasa okręgowa"], "Czwarta liga kobiet", MAIN) is None


def test_futsal_requires_futsal_license():
    assert check_license(["Sędzia TopAmator A (w tym zawodowi)"], "I liga futsal", MAIN) is not None
    assert check_license(["Sędzia I liga futsal i piłka plażowa"], "I liga futsal", MAIN) is None


def test_catalog_lists_every_license_once_with_single_trial_type():
    names = [lic["name"] for g in license_catalog() for lic in g["licenses"]]
    assert sorted(names) == sorted([*LICENSE_RULES, "Obserwator"])
    assert [n for n in names if "próbny" in n] == ["Sędzia próbny (C)"]


def test_generator_skips_unlicensed_referee_and_manual_assignment_warns(client):
    venue = client.post("/api/venues", json={"name": "Stadion", "city": "Warszawa", "latitude": 52.19, "longitude": 20.88}).json()
    body = {"city": "Warszawa", "latitude": 52.19, "longitude": 20.88}
    low = client.post("/api/referees", json={**body, "first_name": "Adam", "last_name": "Bklasowy", "licenses": ["Sędzia klasa B"]}).json()
    high = client.post("/api/referees", json={**body, "first_name": "Ewa", "last_name": "Czwartoligowa", "licenses": ["Sędzia IV liga"]}).json()
    for r in (low, high):
        client.post("/api/availability", json={"referee_id": r["id"], "date": "2026-10-10"})
    m = client.post("/api/matches", json={"date": "2026-10-10", "start_time": "12:00", "estimated_end_time": "13:45",
                                          "league": "IV liga", "home_team": "A", "away_team": "B", "venue_id": venue["id"]}).json()
    day = {"date_from": "2026-10-10", "date_to": "2026-10-10"}
    preview = client.post("/api/optimization/generate", json=day).json()
    assert [a["referee_id"] for a in preview["assignments"]] == [high["id"]]

    cands = {c["referee_id"]: c for c in client.get("/api/assignments/candidates", params={"match_id": m["id"]}).json()}
    assert not cands[low["id"]]["feasible"]
    assert "licencja" in cands[low["id"]]["rejection"]
    r = client.post("/api/assignments", json={"match_id": m["id"], "referee_id": low["id"]}).json()
    assert "licencja" in r["warning"]  # admin może przypisać ręcznie, z ostrzeżeniem


def test_licenses_endpoint(client):
    groups = client.get("/api/licenses").json()
    assert [g["title"] for g in groups] == ["Sędziowie", "Asystenci", "Piłka kobiet", "Futsal i piłka plażowa", "Obserwatorzy"]


def test_working_referees_use_known_licenses_and_load(db_session):
    import json

    from app.database.load_working_data import REFEREES_FILE, load_referees
    from app.models import Referee

    records = json.loads(REFEREES_FILE.read_text(encoding="utf-8"))
    assert len(records) > 300
    assert all(set(r["licenses"]) <= set(LICENSE_RULES) for r in records)
    with db_session() as db:
        assert load_referees(db) == len(records)
        assert load_referees(db) == 0  # ponowne wczytanie nie dubluje
        assert db.query(Referee).count() == len(records)


def test_generator_prefers_women_referee_for_womens_match(client):
    venue = client.post("/api/venues", json={"name": "Stadion", "city": "Warszawa", "latitude": 52.19, "longitude": 20.88}).json()
    body = {"city": "Warszawa", "latitude": 52.19, "longitude": 20.88}
    woman = client.post("/api/referees", json={**body, "first_name": "Ewa", "last_name": "Kobieca", "licenses": ["Sędzia I liga kobiet"]}).json()
    man = client.post("/api/referees", json={**body, "first_name": "Jan", "last_name": "Okręgowy", "licenses": ["Sędzia klasa okręgowa"]}).json()
    for r in (woman, man):
        client.post("/api/availability", json={"referee_id": r["id"], "date": "2026-10-10"})
    match = {"date": "2026-10-10", "start_time": "12:00", "estimated_end_time": "13:45", "venue_id": venue["id"]}
    mens = client.post("/api/matches", json={**match, "league": "Klasa A", "home_team": "A", "away_team": "B"}).json()
    womens = client.post("/api/matches", json={**match, "league": "Czwarta liga kobiet", "home_team": "C", "away_team": "D"}).json()
    preview = client.post("/api/optimization/generate", json={"date_from": "2026-10-10", "date_to": "2026-10-10"}).json()
    by_match = {a["match"]["match_id"]: a["referee_id"] for a in preview["assignments"]}
    assert by_match == {womens["id"]: woman["id"], mens["id"]: man["id"]}
