"""Warstwa abstrakcji routingu (odległości i czasy przejazdu).

Dostawcy (wybór w ``get_routing_service``, ``ROUTING_PROVIDER``):

* ``google`` — Google Maps Routes API (``GOOGLE_MAPS_API_KEY``),
* ``osrm`` — własny serwer OSRM na mapie OpenStreetMap (kontener ``osrm``),
* ``haversine`` — szacunek bez sieci: linia prosta × współczynnik krętości dróg,
* ``auto`` (domyślnie) — Google, gdy jest klucz; inaczej OSRM, gdy ustawiono ``OSRM_URL``;
  inaczej szacunek. Google i OSRM w razie awarii liczą szacunkowo (bez zatrzymania generatora).

Reszta systemu korzysta wyłącznie z interfejsu ``RoutingService``.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
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


CacheKey = tuple[tuple[float, float], tuple[float, float]]


class RoutingService(ABC):
    """Interfejs dostawcy tras."""

    name: str = "abstract"

    def prefetch(self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]) -> None:
        """Przygotowanie wielu tras naraz (macierz); domyślnie nic nie robi."""

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


class RouteStore(ABC):
    """Trwała pamięć tras (np. tabela ``route_cache``) — żeby nie płacić dwa razy za tę samą trasę."""

    @abstractmethod
    def load(self, provider: str, keys: Iterable[CacheKey]) -> dict[CacheKey, RouteInfo]: ...

    @abstractmethod
    def save(self, provider: str, routes: dict[CacheKey, RouteInfo]) -> None: ...


class CachedRoutingService(RoutingService):
    """Dekorator z pamięcią podręczną — istotny przy płatnych API (Google Maps).

    Trasy z serwisu głównego trafiają też do ``store`` (baza). Trasy policzone
    szacunkowo po awarii serwisu nie są zapisywane — przy następnym generowaniu
    serwis zostanie zapytany ponownie.
    """

    def __init__(self, inner: RoutingService, store: RouteStore | None = None) -> None:
        self.inner = inner
        self.store = store
        self.name = inner.name
        self._cache: dict[CacheKey, RouteInfo] = {}

    def _remember(self, routes: dict[CacheKey, RouteInfo]) -> None:
        self._cache.update(routes)
        if self.store is not None and self.inner.name != "haversine":
            self.store.save(self.name, {k: v for k, v in routes.items() if v.provider == self.name})

    def prefetch(self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]) -> None:
        wanted = {(o.key(), d.key()): (o, d) for o in origins for d in destinations if o.key() != d.key()}
        missing = [k for k in wanted if k not in self._cache]
        if missing and self.store is not None:
            self._cache.update(self.store.load(self.name, missing))
            missing = [k for k in missing if k not in self._cache]
        get_matrix = getattr(self.inner, "get_matrix", None)
        if not missing or get_matrix is None:
            return
        src = list({wanted[k][0].key(): wanted[k][0] for k in missing}.values())
        dst = list({wanted[k][1].key(): wanted[k][1] for k in missing}.values())
        matrix = get_matrix(src, dst)
        self._remember({(o.key(), d.key()): info for (o, d), info in matrix.items()})

    def get_route(self, origin: GeoPoint, destination: GeoPoint) -> RouteInfo:
        key = (origin.key(), destination.key())
        if key not in self._cache and self.store is not None:
            self._cache.update(self.store.load(self.name, [key]))
        if key not in self._cache:
            self._remember({key: self.inner.get_route(origin, destination)})
        return self._cache[key]

    def get_distance(self, origin: GeoPoint, destination: GeoPoint) -> float:
        return self.get_route(origin, destination).distance_km

    def get_travel_time(self, origin: GeoPoint, destination: GeoPoint) -> float:
        return self.get_route(origin, destination).travel_minutes


def resolve_provider(provider: str, google_api_key: str = "", osrm_url: str = "") -> str:
    """``auto`` → google (jest klucz) → osrm (jest adres serwera) → haversine."""
    if provider != "auto":
        return provider
    if google_api_key:
        return "google"
    if osrm_url:
        return "osrm"
    return "haversine"


def get_routing_service(
    provider: str = "haversine",
    road_factor: float = 1.3,
    avg_speed_kmh: float = 40.0,
    *,
    google_api_key: str = "",
    osrm_url: str = "",
    store: RouteStore | None = None,
) -> RoutingService:
    """Fabryka dostawców routingu."""
    from app.services.routing_providers import (
        FallbackRoutingService,
        GoogleMapsRoutingService,
        OSRMRoutingService,
    )

    estimate = HaversineRoutingService(road_factor=road_factor, avg_speed_kmh=avg_speed_kmh)
    resolved = resolve_provider(provider, google_api_key, osrm_url)
    if resolved == "haversine":
        return CachedRoutingService(estimate)
    if resolved == "google":
        primary = GoogleMapsRoutingService(google_api_key)
    elif resolved == "osrm":
        if not osrm_url:
            raise ValueError("ROUTING_PROVIDER=osrm wymaga OSRM_URL")
        primary = OSRMRoutingService(osrm_url)
    else:
        raise ValueError(f"Nieznany dostawca routingu: {provider}")
    return CachedRoutingService(FallbackRoutingService(primary, estimate), store=store)
