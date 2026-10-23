"""OSRM i Google Maps (odpowiedzi API zasymulowane) + wybór dostawcy i pamięć tras."""

from __future__ import annotations

import json

import httpx
import pytest

from app.services.routing_providers import (
    FallbackRoutingService,
    GoogleMapsRoutingService,
    OSRMRoutingService,
    RoutingError,
)
from app.services.routing_service import (
    CachedRoutingService,
    HaversineRoutingService,
    RouteInfo,
    RouteStore,
    get_routing_service,
    resolve_provider,
)
from tests.factories import LEGIONOWO, PIASECZNO, URSYNOW, WARSZAWA


def client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def osrm_handler(calls: list):
    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        src = request.url.params["sources"].split(";")
        dst = request.url.params["destinations"].split(";")
        dist = [[1000.0 * (int(i) + 1) * 10 + int(j) for j in dst] for i in src]
        dur = [[600.0 for _ in dst] for _ in src]
        return httpx.Response(200, json={"code": "Ok", "distances": dist, "durations": dur})
    return handle


def test_osrm_table_maps_meters_and_seconds():
    calls: list = []
    osrm = OSRMRoutingService("http://osrm:5000", client=client(osrm_handler(calls)))
    m = osrm.get_matrix([WARSZAWA, URSYNOW], [PIASECZNO])
    assert m[(WARSZAWA, PIASECZNO)] == RouteInfo(10.0, 10.0, "osrm")
    assert m[(URSYNOW, PIASECZNO)].distance_km == 20.0
    assert "/table/v1/driving/21.012200,52.229700;" in str(calls[0].url)


def test_osrm_error_code_raises():
    osrm = OSRMRoutingService("http://osrm", client=client(lambda r: httpx.Response(200, json={"code": "NoTable"})))
    with pytest.raises(RoutingError):
        osrm.get_matrix([WARSZAWA], [PIASECZNO])


def test_google_route_matrix_request_and_parsing():
    seen: list = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = json.loads(request.content)
        assert body["travelMode"] == "DRIVE"
        return httpx.Response(200, json=[
            {"originIndex": 0, "destinationIndex": 0, "distanceMeters": 15300, "duration": "1260s", "condition": "ROUTE_EXISTS"},
        ])

    g = GoogleMapsRoutingService("KEY", client=client(handle))
    assert g.get_route(WARSZAWA, PIASECZNO) == RouteInfo(15.3, 21.0, "google")
    assert seen[0].headers["X-Goog-Api-Key"] == "KEY"


def test_fallback_estimates_when_service_down():
    down = OSRMRoutingService("http://osrm", client=client(lambda r: httpx.Response(503)))
    routing = FallbackRoutingService(down, HaversineRoutingService())
    info = routing.get_route(WARSZAWA, LEGIONOWO)
    assert info.provider == "haversine" and info.distance_km > 20
    assert "OSRM" in routing.last_error


class MemoryStore(RouteStore):
    def __init__(self):
        self.data: dict = {}

    def load(self, provider, keys):
        return {k: self.data[(provider, k)] for k in keys if (provider, k) in self.data}

    def save(self, provider, routes):
        self.data.update({(provider, k): v for k, v in routes.items()})


def test_cache_prefetches_matrix_once_and_persists():
    calls: list = []
    store = MemoryStore()
    osrm = OSRMRoutingService("http://osrm", client=client(osrm_handler(calls)))
    cached = CachedRoutingService(FallbackRoutingService(osrm, HaversineRoutingService()), store=store)
    cached.prefetch([WARSZAWA, URSYNOW], [PIASECZNO, LEGIONOWO])
    cached.get_route(WARSZAWA, PIASECZNO)
    cached.get_route(URSYNOW, LEGIONOWO)
    assert len(calls) == 1
    assert len(store.data) == 4
    # nowy proces: trasy z bazy, bez zapytań
    again = CachedRoutingService(FallbackRoutingService(osrm, HaversineRoutingService()), store=store)
    again.prefetch([WARSZAWA], [PIASECZNO])
    assert again.get_distance(WARSZAWA, PIASECZNO) == 10.0
    assert len(calls) == 1


def test_estimates_after_failure_are_not_persisted():
    store = MemoryStore()
    down = OSRMRoutingService("http://osrm", client=client(lambda r: httpx.Response(503)))
    cached = CachedRoutingService(FallbackRoutingService(down, HaversineRoutingService()), store=store)
    cached.prefetch([WARSZAWA], [PIASECZNO])
    assert cached.get_distance(WARSZAWA, PIASECZNO) > 0
    assert store.data == {}


@pytest.mark.parametrize(
    "key,url,expected",
    [("K", "http://osrm", "google"), ("", "http://osrm", "osrm"), ("", "", "haversine")],
)
def test_auto_prefers_google_then_osrm_then_estimate(key, url, expected):
    assert resolve_provider("auto", key, url) == expected
    assert get_routing_service("auto", google_api_key=key, osrm_url=url).name == expected


def test_db_route_store_roundtrip(db_session):
    from app.services.route_cache_store import DbRouteStore

    db = db_session()
    store = DbRouteStore(db)
    key = (WARSZAWA.key(), PIASECZNO.key())
    store.save("osrm", {key: RouteInfo(18.4, 24.0, "osrm")})
    store.save("osrm", {key: RouteInfo(18.4, 24.0, "osrm")})  # bez duplikatu
    assert store.load("osrm", [key]) == {key: RouteInfo(18.4, 24.0, "osrm")}
    assert store.load("google", [key]) == {}
