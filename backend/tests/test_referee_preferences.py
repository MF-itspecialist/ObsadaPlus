"""Preferowane ligi, unikane kluby, konflikt interesów i ograniczenie do podokręgu."""

from __future__ import annotations

from dataclasses import replace

from app.optimization import AssignmentGenerator, Problem
from app.optimization.clubs import club_matches
from app.services.routing_service import GeoPoint, HaversineRoutingService
from tests.factories import LEGIONOWO, WARSZAWA, referee, slot


def _match(mid, league="Klasa A – Warszawa I", home="Agape II Białołęka", away="KS Ursus", region="Warszawa"):
    return replace(slot(mid, WARSZAWA, "12:00", "13:45"), league=league, home_team=home, away_team=away, venue_region=region)


def _ref(rid, home=WARSZAWA, **kw):
    return replace(referee(home, id=rid), licenses=("Sędzia IV liga",), region="Warszawa", **kw)


def _run(slots, refs):
    return AssignmentGenerator(HaversineRoutingService()).generate_assignments(Problem(slots, refs))


def test_club_names_match_reserves_and_polish_letters():
    assert club_matches("Agape Białołęka", "Agape II Białołęka (Warszawa)")
    assert club_matches("agape bialoleka", "Agape Białołęka")
    assert club_matches("Ursus", "KS Ursus Warszawa")
    assert not club_matches("Ursus Warszawa", "Znicz Pruszków")
    assert not club_matches("", "Znicz Pruszków")


def test_conflict_of_interest_is_a_hard_constraint():
    near = _ref(1, conflict_clubs=("Agape Białołęka",))  # najbliżej, ale związany z gospodarzem
    far = _ref(2, home=LEGIONOWO)
    result = _run([_match(1)], [near, far])
    assert [a.referee_id for a in result.assignments] == [2]

    alone = _run([_match(1)], [near])
    assert alone.assignments == []
    assert alone.unassigned[0].reasons[0].code == "CONFLICT_OF_INTEREST"


def test_avoided_club_only_when_nobody_else():
    near = _ref(1, avoided_clubs=("Ursus",))
    far = _ref(2, home=LEGIONOWO)
    assert [a.referee_id for a in _run([_match(1)], [near, far]).assignments] == [2]
    only = _run([_match(1)], [near]).assignments[0]
    assert only.referee_id == 1
    assert only.explanation["score_breakdown"]["avoided_club_penalty"] > 0
    assert any("unikać klubu Ursus" in r for r in only.explanation["reasons"])


def test_preferred_leagues_steer_the_choice():
    """Klasa A: bliższy sędzia woli tylko IV ligę, więc mecz dostaje trochę dalszy."""
    picky = _ref(1, preferred_leagues=("IV liga",))
    other = _ref(2, home=GeoPoint(52.25, 21.0, "Żoliborz"))
    klasa_a = _match(1)
    assert _run([klasa_a], [replace(picky, preferred_leagues=()), other]).assignments[0].referee_id == 1
    chosen = _run([klasa_a], [picky, other]).assignments[0]
    assert chosen.referee_id == 2
    # IV liga pozostaje dla niego: preferencja nie karze, gdy liga pasuje
    iv_liga = _match(2, league="IV liga – mazowiecka")
    assert _run([iv_liga], [picky, other]).assignments[0].referee_id == 1


def test_own_region_only():
    local = _ref(1, own_region_only=True)
    elsewhere = _match(1, region="Płock")
    result = _run([elsewhere], [local])
    assert result.unassigned[0].reasons[0].code == "OUTSIDE_REGION"
    assert _run([_match(2)], [local]).assignments[0].referee_id == 1


def test_referee_api_validates_and_cleans_preferences(client):
    body = {"first_name": "Jan", "last_name": "Kowalski", "city": "Warszawa", "address": "Ursynów",
            "latitude": 52.15, "longitude": 21.03}
    bad = client.post("/api/referees", json={**body, "preferred_leagues": ["Liga mistrzów"]})
    assert bad.status_code == 422
    r = client.post("/api/referees", json={
        **body, "preferred_leagues": ["IV liga"], "avoided_clubs": [" Ursus ", "Ursus", ""],
        "conflict_clubs": ["Agape Białołęka"], "own_region_only": True,
    }).json()
    assert r["avoided_clubs"] == ["Ursus"] and r["own_region_only"] is True
    assert "IV liga" in client.get("/api/licenses/levels").json()
    assert client.get("/api/matches/clubs").json() == []
