from app.optimization.domain import OptimizationSettings
from app.optimization.scoring import distance_bracket_penalty, load_penalty
from app.services.routing_service import CachedRoutingService, HaversineRoutingService, haversine_km
from tests.factories import LEGIONOWO, PIASECZNO, URSYNOW, WARSZAWA


def test_haversine_known_distance():
    # Warszawa Centrum – Legionowo ≈ 20 km w linii prostej
    assert 18 < haversine_km(WARSZAWA, LEGIONOWO) < 22


def test_road_distance_and_time():
    r = HaversineRoutingService(road_factor=1.3, avg_speed_kmh=40, fixed_overhead_minutes=5)
    km = r.get_distance(URSYNOW, PIASECZNO)
    assert km == round(haversine_km(URSYNOW, PIASECZNO) * 1.3, 2)
    assert r.get_travel_time(URSYNOW, PIASECZNO) == round(km / 40 * 60 + 5, 1)
    assert r.get_travel_time(URSYNOW, URSYNOW) == 0


def test_cached_routing_returns_same_values():
    inner = HaversineRoutingService()
    cached = CachedRoutingService(inner)
    assert cached.get_route(WARSZAWA, LEGIONOWO) == cached.get_route(WARSZAWA, LEGIONOWO)
    assert cached.get_distance(WARSZAWA, LEGIONOWO) == inner.get_distance(WARSZAWA, LEGIONOWO)


def test_distance_brackets_from_spec():
    s = OptimizationSettings()
    assert [distance_bracket_penalty(km, s) for km in (5, 15, 25, 40, 60, 90)] == [0, 10, 30, 70, 150, 300]


def test_load_penalty_small_for_second_big_for_third():
    second = load_penalty(2, preferred=2, weight=20, within_factor=0.25, over_factor=1.5)
    third = load_penalty(3, preferred=2, weight=20, within_factor=0.25, over_factor=1.5)
    assert load_penalty(1, 2, 20, 0.25, 1.5) == 0
    assert second == 5
    assert third - second == 30
