"""Optymalizacja całego okresu naraz (CP-SAT) i powrót do metody zachłannej."""

from __future__ import annotations

import random
from dataclasses import replace

from app.optimization import AssignmentGenerator, Problem
from app.optimization import cpsat
from app.optimization.cpsat import CpSatStrategy, result_quality
from app.services.routing_service import HaversineRoutingService
from tests.factories import LEGIONOWO, OTWOCK, PIASECZNO, PRUSZKOW, URSYNOW, WARSZAWA, referee, slot


def _run(problem, strategy=None):
    return AssignmentGenerator(HaversineRoutingService(), strategy).generate_assignments(problem)


def _trap():
    """Zachłanny bierze bliższego A na mecz 1, a A był jedynym, który może sędziować mecz 2."""
    m1 = slot(1, WARSZAWA, "12:00", "13:45")
    m2 = slot(2, PRUSZKOW, "12:30", "14:15")
    a = referee(WARSZAWA, id=1)
    b = referee(URSYNOW, id=2, available_from="10:00", available_to="14:00")  # na mecz 2 już nie zdąży
    return Problem([m1, m2], [a, b])


def test_greedy_falls_into_the_trap_cpsat_does_not():
    greedy = _run(_trap())
    assert len(greedy.assignments) == 1

    result = _run(_trap(), CpSatStrategy(time_limit_s=5))
    assert {a.slot.match_id: a.referee_id for a in result.assignments} == {1: 2, 2: 1}
    assert result.unassigned == []
    assert result.stats.optimizer == "cpsat"
    assert "obsadzone miejsca +1" in result.stats.optimizer_note
    # pary z optymalizacji nie udają ręcznych zmian i mają zwykłe uzasadnienie
    assert not any(a.manually_modified for a in result.assignments)
    assert all(a.explanation["reasons"] for a in result.assignments)


def test_falls_back_to_greedy_without_ortools(monkeypatch):
    monkeypatch.setattr(cpsat, "ortools_available", lambda: False)
    result = _run(_trap(), CpSatStrategy(time_limit_s=5))
    assert len(result.assignments) == 1
    assert result.stats.optimizer == "greedy"
    assert "OR-Tools" in result.stats.optimizer_note


def test_falls_back_to_greedy_when_solver_crashes(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("x")

    monkeypatch.setattr(CpSatStrategy, "_optimize", boom)
    result = _run(_trap(), CpSatStrategy(time_limit_s=5))
    assert len(result.assignments) == 1
    assert result.stats.optimizer == "greedy"


def test_never_worse_than_greedy_on_a_busy_weekend():
    rnd = random.Random(7)
    venues = [WARSZAWA, URSYNOW, PIASECZNO, LEGIONOWO, PRUSZKOW, OTWOCK]
    slots = []
    for mid in range(1, 25):
        h = rnd.choice(["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"])
        end = f"{int(h[:2]) + 1}:45"
        slots.append(slot(mid, rnd.choice(venues), h, end))
    refs = [
        referee(rnd.choice(venues), id=i, max_day=rnd.choice([1, 2, 3]), preferred_day=1)
        for i in range(1, 12)
    ]
    problem = Problem(slots, refs)
    greedy = _run(problem)
    optimized = _run(problem, CpSatStrategy(time_limit_s=10))
    assert result_quality(optimized) <= result_quality(greedy)
    # żaden sędzia nie ma dwóch meczów, na które nie zdąży
    by_ref = {}
    for a in optimized.assignments:
        by_ref.setdefault(a.referee_id, []).append(a.slot)
    for rid, ss in by_ref.items():
        ss.sort(key=lambda s: s.start)
        assert len(ss) <= next(r for r in refs if r.id == rid).max_matches_per_day
        for x, y in zip(ss, ss[1:]):
            assert x.end <= y.required_arrival


def test_generate_uses_setting(client, monkeypatch):
    settings = client.get("/api/settings").json()
    assert settings["optimizer"] == "cpsat"
    assert client.put("/api/settings", json={**settings, "optimizer": "greedy"}).status_code == 200
    assert client.put("/api/settings", json={**settings, "optimizer": "magia"}).status_code == 422
