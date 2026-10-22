"""Kolejność obsadzania: najpierw IV liga, potem V liga, okręgówka, klasa A, B…"""

from __future__ import annotations

from dataclasses import replace

from app.optimization import AssignmentGenerator, Problem
from app.optimization.generator import league_priority
from app.services.routing_service import HaversineRoutingService
from tests.factories import BIALOLEKA, LEGIONOWO, URSYNOW, WARSZAWA, referee, slot


def test_league_priority_order():
    leagues = ["Klasa B – Płock", "Junior A1", "IV liga – mazowiecka", "Klasa A – Radom I",
               "Liga okręgowa – Warszawa I", "V liga – mazowiecka II"]
    assert sorted(leagues, key=league_priority) == [
        "IV liga – mazowiecka", "V liga – mazowiecka II", "Liga okręgowa – Warszawa I",
        "Klasa A – Radom I", "Klasa B – Płock", "Junior A1",
    ]


def test_higher_league_gets_the_referee_first_even_if_it_starts_later():
    """Jedyny sędzia z licencją IV ligi trafia na IV ligę, nie na wcześniejszą klasę A."""
    klasa_a = replace(slot(1, URSYNOW, "11:00", "12:45"), league="Klasa A – Warszawa I")
    iv_liga = replace(slot(2, WARSZAWA, "12:00", "13:45"), league="IV liga – mazowiecka")
    top = replace(referee(WARSZAWA, id=1), licenses=("Sędzia IV liga",))
    other = replace(referee(LEGIONOWO, id=2), licenses=("Sędzia klasa A",))

    result = AssignmentGenerator(HaversineRoutingService()).generate_assignments(Problem([klasa_a, iv_liga], [top, other]))

    by_match = {a.slot.match_id: a.referee_id for a in result.assignments}
    assert by_match == {2: 1, 1: 2}
    assert result.unassigned == []


def test_distance_counts_from_previous_match_after_reordering():
    """Mecz obsadzony później, ale wcześniej w ciągu dnia: dojazd na drugi mecz liczony z boiska."""
    morning = replace(slot(1, BIALOLEKA, "10:00", "11:45"), league="Klasa B – Warszawa I")
    afternoon = replace(slot(2, LEGIONOWO, "15:00", "16:45"), league="IV liga – mazowiecka")
    ref = replace(referee(WARSZAWA, id=1), licenses=("Sędzia IV liga",))

    result = AssignmentGenerator(HaversineRoutingService()).generate_assignments(Problem([morning, afternoon], [ref]))

    later = next(a for a in result.assignments if a.slot.match_id == 2)
    direct = HaversineRoutingService().get_distance(BIALOLEKA, LEGIONOWO)
    assert later.distance_km == direct
