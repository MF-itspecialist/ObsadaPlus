"""Testy generatora obsady (scenariusze z sekcji 38 specyfikacji + reguła z sekcji 39)."""

from __future__ import annotations

import datetime as dt

from app.optimization import AssignmentGenerator, FixedBooking, OptimizationSettings, Problem
from app.services.routing_service import HaversineRoutingService
from tests.factories import (
    BIALOLEKA,
    GRODZISK,
    LEGIONOWO,
    OTWOCK,
    PIASECZNO,
    PRUSZKOW,
    SATURDAY,
    SOCHACZEW,
    URSYNOW,
    WARSZAWA,
    FixedTimeRouting,
    referee,
    slot,
)


def generate(problem: Problem, routing=None):
    return AssignmentGenerator(routing or HaversineRoutingService()).generate_assignments(problem)


def assigned_to(result, match_id: int) -> int | None:
    return next((a.referee_id for a in result.assignments if a.slot.match_id == match_id), None)


def reason_codes(result, match_id: int) -> set[str]:
    u = next(u for u in result.unassigned if u.slot.match_id == match_id)
    return {r.code for r in u.reasons}


# 1. sędzia niedostępny ----------------------------------------------------------
def test_unavailable_referee_is_skipped():
    near = referee(URSYNOW, id=1, available=False)
    far = referee(PIASECZNO, id=2)
    result = generate(Problem([slot(1, URSYNOW, "14:00", "15:45")], [near, far]))
    assert assigned_to(result, 1) == 2


def test_referee_without_availability_entry_is_unavailable_by_default():
    no_entry = referee(URSYNOW, id=1, days=())
    result = generate(Problem([slot(1, URSYNOW, "14:00", "15:45")], [no_entry]))
    assert assigned_to(result, 1) is None
    assert reason_codes(result, 1) == {"NOT_AVAILABLE_DAY"}


def test_match_outside_availability_window():
    # dostępny od 13:30, a przyjazd wymagany na 13:15
    ref = referee(URSYNOW, id=1, available_from="13:30", available_to="20:00")
    result = generate(Problem([slot(1, URSYNOW, "14:00", "15:45")], [ref]))
    assert reason_codes(result, 1) == {"OUTSIDE_TIME_WINDOW"}


# 2. konflikt dwóch meczów -------------------------------------------------------
def test_overlapping_matches_cannot_share_referee():
    ref = referee(URSYNOW, id=1)
    slots = [slot(1, URSYNOW, "14:00", "15:45"), slot(2, URSYNOW, "15:00", "16:45")]
    result = generate(Problem(slots, [ref]))
    assert assigned_to(result, 1) == 1
    assert assigned_to(result, 2) is None
    assert reason_codes(result, 2) == {"TIME_CONFLICT"}


# 3. brak czasu na transport (przykład z sekcji 11) ------------------------------
def test_not_enough_travel_time_between_matches():
    # Mecz A 10:00–11:45, mecz B 13:00 (przyjazd 12:15). 11:45 + 35 + 15 = 12:35 > 12:15.
    ref = referee(WARSZAWA, id=1)
    slots = [slot(1, LEGIONOWO, "10:00", "11:45"), slot(2, OTWOCK, "13:00", "14:45")]
    result = generate(Problem(slots, [ref]), routing=FixedTimeRouting(minutes=35))
    assert assigned_to(result, 1) == 1
    assert assigned_to(result, 2) is None
    assert reason_codes(result, 2) == {"NO_TRAVEL_TIME"}


def test_enough_travel_time_between_matches():
    # 11:45 + 20 + 15 = 12:20 <= 12:30 (mecz 13:15)
    ref = referee(WARSZAWA, id=1)
    slots = [slot(1, LEGIONOWO, "10:00", "11:45"), slot(2, OTWOCK, "13:15", "15:00")]
    result = generate(Problem(slots, [ref]), routing=FixedTimeRouting(minutes=20))
    assert assigned_to(result, 2) == 1


def test_safety_buffer_is_configurable():
    ref = referee(WARSZAWA, id=1)
    slots = [slot(1, LEGIONOWO, "10:00", "11:45"), slot(2, OTWOCK, "13:00", "14:45")]
    settings = OptimizationSettings(transport_safety_buffer_minutes=0)
    # 11:45 + 30 + 0 = 12:15 <= 12:15
    result = generate(Problem(slots, [ref], settings=settings), routing=FixedTimeRouting(minutes=30))
    assert assigned_to(result, 2) == 1


def test_new_match_must_not_break_travel_to_later_fixed_match():
    # Ręcznie przypisany mecz o 13:00; nowy mecz 10:00–11:45 nie może go zablokować.
    ref = referee(WARSZAWA, id=1)
    fixed = FixedBooking(slot=slot(2, OTWOCK, "13:00", "14:45"), referee_id=1)
    result = generate(
        Problem([slot(1, LEGIONOWO, "10:00", "11:45"), fixed.slot], [ref], fixed=[fixed]),
        routing=FixedTimeRouting(minutes=35),
    )
    assert assigned_to(result, 2) == 1
    assert assigned_to(result, 1) is None
    assert reason_codes(result, 1) == {"NO_TRAVEL_TIME"}


# 4. przekroczenie max_matches_per_day ------------------------------------------
def test_max_matches_per_day_is_hard_limit():
    ref = referee(URSYNOW, id=1, preferred_day=1, max_day=1)
    slots = [slot(1, URSYNOW, "10:00", "11:45"), slot(2, URSYNOW, "14:00", "15:45")]
    result = generate(Problem(slots, [ref]))
    assert assigned_to(result, 1) == 1
    assert assigned_to(result, 2) is None
    assert reason_codes(result, 2) == {"DAILY_LIMIT"}


def test_fourth_match_is_never_allowed_with_max_three():
    ref = referee(URSYNOW, id=1, preferred_day=2, max_day=3)
    times = [("09:00", "10:30"), ("11:30", "13:00"), ("14:00", "15:30"), ("16:30", "18:00")]
    slots = [slot(i + 1, URSYNOW, s, e) for i, (s, e) in enumerate(times)]
    result = generate(Problem(slots, [ref]))
    assert [assigned_to(result, i) for i in (1, 2, 3, 4)] == [1, 1, 1, None]
    assert reason_codes(result, 4) == {"DAILY_LIMIT"}


def test_max_matches_per_weekend_is_hard_limit():
    ref = referee(URSYNOW, id=1, max_weekend=2)
    slots = [
        slot(1, URSYNOW, "10:00", "11:45"),
        slot(2, URSYNOW, "14:00", "15:45"),
        slot(3, URSYNOW, "10:00", "11:45", day=SATURDAY + dt.timedelta(days=1)),
    ]
    result = generate(Problem(slots, [ref]))
    assert assigned_to(result, 3) is None
    assert reason_codes(result, 3) == {"WEEKEND_LIMIT"}


# 5. wybór bliższego sędziego ----------------------------------------------------
def test_closer_referee_is_preferred():
    far = referee(GRODZISK, id=1)
    near = referee(URSYNOW, id=2)
    result = generate(Problem([slot(1, PIASECZNO, "14:00", "15:45")], [far, near]))
    assert assigned_to(result, 1) == 2
    chosen = result.assignments[0]
    assert chosen.distance_km is not None and chosen.distance_km < 15
    assert any("odległość" in r for r in chosen.explanation["reasons"])


# 6. wcześniejszy mecz zmienia punkt startowy -----------------------------------
def test_previous_match_is_travel_origin():
    routing = HaversineRoutingService()
    ref = referee(WARSZAWA, id=1)
    slots = [slot(1, LEGIONOWO, "10:00", "11:45"), slot(2, BIALOLEKA, "14:00", "15:45")]
    result = generate(Problem(slots, [ref]), routing=routing)
    second = next(a for a in result.assignments if a.slot.match_id == 2)
    assert second.explanation["origin"] == "previous_match"
    assert second.distance_km == routing.get_distance(LEGIONOWO, BIALOLEKA)
    assert second.distance_km != routing.get_distance(WARSZAWA, BIALOLEKA)


def test_previous_match_location_can_make_far_living_referee_best():
    # X mieszka w Otwocku, ale ma mecz w Legionowie; Y mieszka w Piasecznie.
    x = referee(OTWOCK, id=1, name="X")
    y = referee(PIASECZNO, id=2, name="Y")
    first = FixedBooking(slot=slot(1, LEGIONOWO, "10:00", "11:45"), referee_id=1)
    problem = Problem([first.slot, slot(2, BIALOLEKA, "14:00", "15:45")], [x, y], fixed=[first])
    result = generate(problem)
    assert assigned_to(result, 2) == 1


# 7. równomierne rozdawanie -----------------------------------------------------
def test_matches_are_spread_evenly_when_logistics_are_equal():
    refs = [referee(URSYNOW, id=i) for i in (1, 2, 3)]
    slots = [slot(i, URSYNOW, f"{8 + 3 * i:02d}:00", f"{9 + 3 * i:02d}:45") for i in (1, 2, 3)]
    result = generate(Problem(slots, refs))
    assert sorted(a.referee_id for a in result.assignments) == [1, 2, 3]


# 8. brak dostępnego sędziego ---------------------------------------------------
def test_no_referee_available_gives_unassigned_with_reasons():
    refs = [referee(URSYNOW, id=1, available=False), referee(PIASECZNO, id=2, active=False)]
    result = generate(Problem([slot(1, URSYNOW, "14:00", "15:45")], refs))
    assert result.assignments == []
    assert result.stats.matches_unassigned == 1
    assert reason_codes(result, 1) == {"NOT_AVAILABLE_DAY"}


# Reguła z sekcji 39: logistyka ważniejsza niż idealna równość ------------------
def test_logistics_beat_equal_distribution():
    a = referee(URSYNOW, id=1, name="A", preferred_day=2, max_day=3)
    b = referee(SOCHACZEW, id=2, name="B")
    fixed = [
        FixedBooking(slot=slot(1, URSYNOW, "09:00", "10:30"), referee_id=1, in_scope=False),
        FixedBooking(slot=slot(2, URSYNOW, "11:30", "13:00"), referee_id=1, in_scope=False),
    ]
    target = slot(3, PIASECZNO, "15:00", "16:45")
    routing = HaversineRoutingService()
    assert routing.get_distance(SOCHACZEW, PIASECZNO) > 50
    result = generate(Problem([target], [a, b], fixed=fixed), routing=routing)
    assert assigned_to(result, 3) == 1


def test_manual_assignment_is_kept_and_reported():
    near = referee(URSYNOW, id=1)
    far = referee(PRUSZKOW, id=2)
    manual = FixedBooking(slot=slot(1, URSYNOW, "14:00", "15:45"), referee_id=2)
    result = generate(Problem([manual.slot], [near, far], fixed=[manual]))
    a = result.assignments[0]
    assert a.referee_id == 2 and a.manually_modified


def test_stats_are_computed():
    refs = [referee(URSYNOW, id=1), referee(PIASECZNO, id=2)]
    slots = [slot(1, URSYNOW, "10:00", "11:45"), slot(2, PIASECZNO, "10:00", "11:45")]
    stats = generate(Problem(slots, refs)).stats
    assert stats.matches_total == 2 and stats.matches_assigned == 2
    assert stats.active_referees == 2
    assert stats.avg_matches_per_referee == 1.0
    assert stats.total_distance_km >= 0
    assert stats.conflicts == 0


# Dni obsadowe piątek–poniedziałek ---------------------------------------------
def test_round_covers_friday_to_monday():
    from app.optimization.domain import round_bounds, weekend_key

    friday, monday, tuesday = SATURDAY - dt.timedelta(days=1), SATURDAY + dt.timedelta(days=2), SATURDAY + dt.timedelta(days=3)
    assert {weekend_key(d) for d in (friday, SATURDAY, SATURDAY + dt.timedelta(days=1), monday)} == {SATURDAY}
    assert weekend_key(tuesday) == SATURDAY + dt.timedelta(days=7)
    assert round_bounds(SATURDAY) == (SATURDAY - dt.timedelta(days=4), monday)


def test_weekend_limit_counts_friday_and_monday():
    friday, monday = SATURDAY - dt.timedelta(days=1), SATURDAY + dt.timedelta(days=2)
    ref = referee(URSYNOW, id=1, max_weekend=2, days=(friday, SATURDAY, monday))
    slots = [
        slot(1, URSYNOW, "18:00", "19:45", day=friday),
        slot(2, URSYNOW, "10:00", "11:45"),
        slot(3, URSYNOW, "18:00", "19:45", day=monday),
    ]
    result = generate(Problem(slots, [ref]))
    assert assigned_to(result, 1) == 1 and assigned_to(result, 2) == 1
    assert reason_codes(result, 3) == {"WEEKEND_LIMIT"}
