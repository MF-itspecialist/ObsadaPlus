"""Prawdziwe trasy drogowe: OSRM (własny serwer, bez klucza) i Google Maps (Routes API).

Oba serwisy liczą dojazd samochodem po drogach. Generator najpierw prosi o macierz
odległości dla wszystkich par (dom sędziego / obiekt → obiekt) jednym lub kilkoma
zapytaniami (``get_matrix``), a pojedyncze trasy biorą się potem z pamięci podręcznej.

Gdy serwis jest niedostępny, ``FallbackRoutingService`` liczy trasę szacunkowo
(linia prosta × współczynnik), żeby generowanie obsady nigdy nie stanęło.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence

import httpx

from app.services.routing_service import GeoPoint, RouteInfo, RoutingService

log = logging.getLogger(__name__)


class RoutingError(RuntimeError):
    """Serwis tras nie odpowiedział lub zwrócił błąd."""


Matrix = dict[tuple[GeoPoint, GeoPoint], RouteInfo]


def _chunks(items: Sequence[GeoPoint], size: int) -> list[Sequence[GeoPoint]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


class MatrixRoutingService(RoutingService):
    """Wspólna część serwisów z API macierzy odległości."""

    def get_matrix(self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]) -> Matrix:
        raise NotImplementedError

    def get_route(self, origin: GeoPoint, destination: GeoPoint) -> RouteInfo:
        if origin.key() == destination.key():
            return RouteInfo(0.0, 0.0, self.name)
        return self.get_matrix([origin], [destination])[(origin, destination)]

    def get_distance(self, origin: GeoPoint, destination: GeoPoint) -> float:
        return self.get_route(origin, destination).distance_km

    def get_travel_time(self, origin: GeoPoint, destination: GeoPoint) -> float:
        return self.get_route(origin, destination).travel_minutes


class OSRMRoutingService(MatrixRoutingService):
    """OSRM (Open Source Routing Machine) na mapie OpenStreetMap — kontener ``osrm`` w docker-compose."""

    name = "osrm"
    # OSRM domyślnie przyjmuje do 100 punktów w jednym zapytaniu /table.
    max_points = 100

    def __init__(self, base_url: str, timeout: float = 15.0, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=timeout)

    def get_matrix(self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]) -> Matrix:
        result: Matrix = {}
        half = self.max_points // 2
        for src in _chunks(list(origins), half):
            for dst in _chunks(list(destinations), half):
                result.update(self._table(src, dst))
        return result

    def _table(self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]) -> Matrix:
        points = [*origins, *destinations]
        coords = ";".join(f"{p.longitude:.6f},{p.latitude:.6f}" for p in points)
        params = {
            "sources": ";".join(str(i) for i in range(len(origins))),
            "destinations": ";".join(str(len(origins) + i) for i in range(len(destinations))),
            "annotations": "duration,distance",
        }
        try:
            resp = self.client.get(f"{self.base_url}/table/v1/driving/{coords}", params=params)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RoutingError(f"OSRM niedostępny: {exc}") from exc
        if data.get("code") != "Ok":
            raise RoutingError(f"OSRM: {data.get('code')} {data.get('message', '')}".strip())
        result: Matrix = {}
        for i, o in enumerate(origins):
            for j, d in enumerate(destinations):
                meters, seconds = data["distances"][i][j], data["durations"][i][j]
                if meters is None or seconds is None:
                    raise RoutingError(f"OSRM: brak trasy {o.label or o.key()} → {d.label or d.key()}")
                result[(o, d)] = RouteInfo(round(meters / 1000, 2), round(seconds / 60, 1), self.name)
        return result


_DURATION = re.compile(r"^(\d+(?:\.\d+)?)s$")


class GoogleMapsRoutingService(MatrixRoutingService):
    """Google Maps Routes API (``computeRouteMatrix``) — wymaga klucza z włączonym Routes API."""

    name = "google"
    url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    # Limit Google: iloczyn źródeł i celów ≤ 625 (bez ruchu drogowego); bierzemy 25 × 25.
    max_side = 25

    def __init__(self, api_key: str, timeout: float = 20.0, client: httpx.Client | None = None) -> None:
        if not api_key:
            raise ValueError("Brak klucza Google Maps (GOOGLE_MAPS_API_KEY)")
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=timeout)

    @staticmethod
    def _waypoint(p: GeoPoint) -> dict:
        return {"waypoint": {"location": {"latLng": {"latitude": p.latitude, "longitude": p.longitude}}}}

    def get_matrix(self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]) -> Matrix:
        result: Matrix = {}
        for src in _chunks(list(origins), self.max_side):
            for dst in _chunks(list(destinations), self.max_side):
                result.update(self._matrix(src, dst))
        return result

    def _matrix(self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]) -> Matrix:
        body = {
            "origins": [self._waypoint(p) for p in origins],
            "destinations": [self._waypoint(p) for p in destinations],
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_UNAWARE",
        }
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "originIndex,destinationIndex,distanceMeters,duration,condition",
        }
        try:
            resp = self.client.post(self.url, json=body, headers=headers)
            resp.raise_for_status()
            elements = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RoutingError(f"Google Maps niedostępne: {exc}") from exc
        result: Matrix = {}
        for el in elements:
            o, d = origins[el.get("originIndex", 0)], destinations[el.get("destinationIndex", 0)]
            if el.get("condition") != "ROUTE_EXISTS":
                raise RoutingError(f"Google Maps: brak trasy {o.label or o.key()} → {d.label or d.key()}")
            m = _DURATION.match(el.get("duration", "0s"))
            seconds = float(m[1]) if m else 0.0
            result[(o, d)] = RouteInfo(round(el.get("distanceMeters", 0) / 1000, 2), round(seconds / 60, 1), self.name)
        missing = [(o, d) for o in origins for d in destinations if (o, d) not in result]
        if missing:
            raise RoutingError(f"Google Maps: niepełna odpowiedź ({len(missing)} brakujących tras)")
        return result


class FallbackRoutingService(MatrixRoutingService):
    """Najpierw serwis główny (Google/OSRM); gdy zawiedzie — szacunek z ``fallback``."""

    def __init__(self, primary: MatrixRoutingService, fallback: RoutingService) -> None:
        self.primary = primary
        self.fallback = fallback
        self.name = primary.name
        self.last_error: str | None = None

    def get_matrix(self, origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint]) -> Matrix:
        try:
            return self.primary.get_matrix(origins, destinations)
        except RoutingError as exc:
            if self.last_error != str(exc):
                log.warning("%s — liczę trasy szacunkowo (%s)", exc, self.fallback.name)
            self.last_error = str(exc)
            return {(o, d): self.fallback.get_route(o, d) for o in origins for d in destinations}
