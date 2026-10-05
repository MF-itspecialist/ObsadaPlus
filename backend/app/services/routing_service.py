"""Warstwa abstrakcji routingu (odległości i czasy przejazdu).

MVP korzysta z ``HaversineRoutingService`` — odległość po łuku wielkiego koła
przemnożona przez współczynnik krętości dróg oraz średnia prędkość przejazdu.
Kolejne implementacje (``GoogleMapsRoutingService``, ``OSRMRoutingService``)
wystarczy dopisać jako podklasy ``RoutingService`` i zarejestrować w
``get_routing_service``. Reszta systemu korzysta wyłącznie z interfejsu.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GeoPoint:
    """Punkt geograficzny; ``label`` służy wyłącznie do opisów w UI."""

    latitude: float
    longitude: float
    label: str = ""

    def key(self) -> tuple[float, float]:
        # Zaokrąglenie do ~10 m — klucz cache dla zewnętrznych API.
        return (round(self.latitude, 4), round(self.longitude, 4))


@dataclass(frozen=True)
class RouteInfo:
    distance_km: float
    travel_minutes: float
    provider: str


class RoutingService(ABC):
    """Interfejs dostawcy tras."""

    name: str = "abstract"

    @abstractmethod
    def get_distance(self, origin: GeoPoint, destination: GeoPoint) -> float:
        """Odległość drogowa w kilometrach."""

    @abstractmethod
    def get_travel_time(self, origin: GeoPoint, destination: GeoPoint) -> float:
        """Czas przejazdu w minutach."""

    def get_route(self, origin: GeoPoint, destination: GeoPoint) -> RouteInfo:
        """Odległość i czas jednym wywołaniem (zewnętrzne API zwracają oba naraz)."""
        return RouteInfo(
            distance_km=self.get_distance(origin, destination),
            travel_minutes=self.get_travel_time(origin, destination),
            provider=self.name,
        )


def haversine_km(a: GeoPoint, b: GeoPoint) -> float:
    """Odległość w linii prostej (km) pomiędzy dwoma punktami."""
    r = 6371.0088
    lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
    dlat = lat2 - lat1
    dlon = math.radians(b.longitude - a.longitude)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


class HaversineRoutingService(RoutingService):
    """Szacowanie trasy bez zewnętrznego API.

    * distance = haversine × ``road_factor`` (drogi nie biegną po linii prostej),
    * time = distance / ``avg_speed_kmh`` + ``fixed_overhead_minutes``
      (wyjazd, parkowanie), o ile punkty nie są tym samym miejscem.
    """

    name = "haversine"

    def __init__(
        self,
        road_factor: float = 1.3,
        avg_speed_kmh: float = 40.0,
        fixed_overhead_minutes: float = 5.0,
    ) -> None:
        if avg_speed_kmh <= 0:
            raise ValueError("avg_speed_kmh musi być dodatnie")
        self.road_factor = road_factor
        self.avg_speed_kmh = avg_speed_kmh
        self.fixed_overhead_minutes = fixed_overhead_minutes

    def get_distance(self, origin: GeoPoint, destination: GeoPoint) -> float:
        return round(haversine_km(origin, destination) * self.road_factor, 2)

    def get_travel_time(self, origin: GeoPoint, destination: GeoPoint) -> float:
        km = self.get_distance(origin, destination)
        if km < 0.1:  # to samo boisko / ten sam adres
            return 0.0
        return round(km / self.avg_speed_kmh * 60 + self.fixed_overhead_minutes, 1)


class CachedRoutingService(RoutingService):
    """Dekorator z pamięcią podręczną — istotny przy płatnych API (Google Maps)."""

    def __init__(self, inner: RoutingService) -> None:
        self.inner = inner
        self.name = inner.name
        self._cache: dict[tuple[tuple[float, float], tuple[float, float]], RouteInfo] = {}

    def get_route(self, origin: GeoPoint, destination: GeoPoint) -> RouteInfo:
        key = (origin.key(), destination.key())
        if key not in self._cache:
            self._cache[key] = self.inner.get_route(origin, destination)
        return self._cache[key]

    def get_distance(self, origin: GeoPoint, destination: GeoPoint) -> float:
        return self.get_route(origin, destination).distance_km

    def get_travel_time(self, origin: GeoPoint, destination: GeoPoint) -> float:
        return self.get_route(origin, destination).travel_minutes


def get_routing_service(
    provider: str = "haversine",
    road_factor: float = 1.3,
    avg_speed_kmh: float = 40.0,
) -> RoutingService:
    """Fabryka dostawców routingu. Tu podłącza się Google Maps / OSRM."""
    if provider == "haversine":
        return CachedRoutingService(
            HaversineRoutingService(road_factor=road_factor, avg_speed_kmh=avg_speed_kmh)
        )
    # elif provider == "osrm": return CachedRoutingService(OSRMRoutingService(base_url=...))
    # elif provider == "google": return CachedRoutingService(GoogleMapsRoutingService(api_key=...))
    raise ValueError(f"Nieznany dostawca routingu: {provider}")
