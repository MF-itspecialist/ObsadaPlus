"""Obsada zespołowa (G + A1 + A2): dobór składu po trasach całego zespołu."""

from __future__ import annotations

from dataclasses import replace

from app.models.enums import RefereeRole
from app.optimization import AssignmentGenerator, OptimizationSettings, Problem
from app.services.routing_service import GeoPoint, HaversineRoutingService
from tests.factories import referee, slot

VENUE = GeoPoint(52.2000, 21.0000, "Stadion")
# ~8 km od stadionu w trzech różnych kierunkach
NORTH = GeoPoint(52.2720, 21.0000, "Północ")
EAST = GeoPoint(52.2000, 21.1170, "Wschód")
WEST = GeoPoint(52.2000, 20.8830, "Zachód")
# ~9 km na południe, wszyscy trzej blisko siebie
SOUTH = GeoPoint(52.1190, 21.0000, "Południe")

CREW = (RefereeRole.MAIN, RefereeRole.ASSISTANT_1, RefereeRole.ASSISTANT_2)


def crew_slots(match_id: int = 1):
    return [slot(match_id, VENUE, "14:00", "15:45", role=r) for r in CREW]


def generate(problem: Problem):
    return AssignmentGenerator(HaversineRoutingService()).generate_assignments(problem)


def crew_ids(result, match_id: int = 1) -> set[int]:
    return {a.referee_id for a in result.assignments if a.slot.match_id == match_id}


def spread_and_cluster():
    spread = [referee(p, id=i) for i, p in enumerate((NORTH, EAST, WEST), start=1)]
    cluster = [referee(SOUTH, id=i) for i in (11, 12, 13)]
    return spread, cluster


def test_crew_that_can_travel_together_wins():
    spread, cluster = spread_and_cluster()
    result = generate(Problem(crew_slots(), spread + cluster))
    assert crew_ids(result) == {11, 12, 13}
    reasons = result.assignments[0].explanation["reasons"]
    assert any(r.startswith("wspólny dojazd zespołu") for r in reasons)


def test_without_route_weight_each_referee_counts_own_distance():
    spread, cluster = spread_and_cluster()
    settings = OptimizationSettings(crew_route_weight=0.0)
    result = generate(Problem(crew_slots(), spread + cluster, settings=settings))
    assert crew_ids(result) == {1, 2, 3}


def test_single_referee_match_uses_own_location():
    spread, cluster = spread_and_cluster()
    result = generate(Problem([slot(1, VENUE, "14:00", "15:45")], spread + cluster))
    assert crew_ids(result) <= {1, 2, 3}
    assert "shared_ride_km" not in result.assignments[0].explanation


def test_one_referee_never_takes_two_roles_and_missing_role_is_reported():
    refs = [referee(VENUE, id=1), referee(SOUTH, id=2)]
    result = generate(Problem(crew_slots(), refs))
    assert len(result.assignments) == 2
    assert crew_ids(result) == {1, 2}
    assert [u.slot.role for u in result.unassigned] == [RefereeRole.ASSISTANT_2]


def test_main_referee_needs_licence_for_the_league():
    league_slots = [replace(s, league="Klasa A") for s in crew_slots()]
    a_class = referee(SOUTH, id=1)
    a_class.licenses = ("Sędzia klasa A",)
    b_class = [referee(SOUTH, id=i) for i in (2, 3)]
    for r in b_class:
        r.licenses = ("Sędzia klasa B",)
    result = generate(Problem(league_slots, [a_class, *b_class]))
    main = next(a for a in result.assignments if a.slot.role == RefereeRole.MAIN)
    assert main.referee_id == 1
    assert crew_ids(result) == {1, 2, 3}
