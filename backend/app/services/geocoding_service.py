"""Geokodowanie: adres → współrzędne geograficzne, miasto i dzielnica.

Administrator wpisuje tylko adres (ulica + miasto); współrzędne potrzebne do
liczenia dojazdów pobieramy automatycznie. Dostawcy:

* ``GoogleGeocoder`` — Google Maps Geocoding API, gdy ustawiono ``GOOGLE_MAPS_API_KEY``,
* ``NominatimGeocoder`` — OpenStreetMap (bez klucza; domyślny na dev).

Reszta systemu korzysta wyłącznie z interfejsu ``Geocoder``.
"""

from __future__ import annotations

import re
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache

import httpx

from app.config import get_config


@dataclass(frozen=True)
class GeocodeResult:
    latitude: float
    longitude: float
    city: str
    # Dzielnica — tylko dla miast podzielonych na dzielnice (np. Warszawa: "Mokotów").
    district: str
    formatted_address: str


class GeocodingError(RuntimeError):
    """Dostawca geokodowania jest niedostępny (sieć, limit zapytań, zły klucz)."""


class Geocoder(ABC):
    name: str = "abstract"

    @abstractmethod
    def geocode(self, address: str, city: str) -> GeocodeResult | None:
        """Zwraca lokalizację adresu albo ``None``, gdy adresu nie znaleziono."""


_STREET_PREFIX = re.compile(r"^\s*(ul\.|ulica)\s*", re.IGNORECASE)
# Skróty rozwijamy, ale nie usuwamy: "Plac Wojska Polskiego" to inna ulica niż "aleja Wojska Polskiego".
_ABBREVIATIONS = ((re.compile(r"^\s*al\.\s*", re.IGNORECASE), "Aleja "), (re.compile(r"^\s*pl\.\s*", re.IGNORECASE), "Plac "),
                  (re.compile(r"^\s*os\.\s*", re.IGNORECASE), "Osiedle "))


def normalize_street(address: str) -> str:
    """'ul. Puławska 100' → 'Puławska 100', 'al. Jerozolimskie 1' → 'Aleja Jerozolimskie 1'."""
    street = _STREET_PREFIX.sub("", address.strip())
    for pattern, full in _ABBREVIATIONS:
        street = pattern.sub(full, street)
    return street


class NominatimGeocoder(Geocoder):
    """OpenStreetMap Nominatim. Limit publicznej instancji: ~1 zapytanie / s."""

    name = "nominatim"
    URL = "https://nominatim.openstreetmap.org/search"

    MIN_INTERVAL_S = 1.0

    def __init__(self, timeout: float = 10.0, viewbox: str = "") -> None:
        self.timeout = timeout
        # "lon1,lat1,lon2,lat2" — najpierw szukamy w tym obszarze (wiele wsi ma tę samą nazwę w różnych województwach).
        self.viewbox = viewbox
        self._lock = threading.Lock()
        self._last_call = 0.0

    def _throttle(self) -> None:
        # Polityka publicznego Nominatim: nie częściej niż raz na sekundę (np. przy imporcie wielu obiektów).
        with self._lock:
            wait = self._last_call + self.MIN_INTERVAL_S - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()

    def _search(self, params: dict[str, str]) -> list[dict]:
        self._throttle()
        params = {**params, "format": "jsonv2", "addressdetails": "1", "limit": "1", "accept-language": "pl"}
        try:
            resp = httpx.get(
                self.URL, params=params, timeout=self.timeout, headers={"User-Agent": "ObsadaPlus/0.1"}
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise GeocodingError(f"Nominatim: {exc}") from exc
        return resp.json()

    def geocode(self, address: str, city: str) -> GeocodeResult | None:
        street = normalize_street(address)
        queries: list[dict[str, str]] = []
        if street and city:
            queries.append({"street": street, "city": city, "country": "Polska"})
        queries.append({"q": ", ".join(p for p in (street, city) if p), "countrycodes": "pl"})
        regions = [{"viewbox": self.viewbox, "bounded": "1"}, {}] if self.viewbox else [{}]
        hits: list[dict] = []
        for region in regions:
            for query in queries:
                hits = self._search({**query, **region})
                if hits:
                    break
            if hits:
                break
        if not hits:
            return None
        hit = hits[0]
        addr = hit.get("address", {})
        found_city = addr.get("city") or addr.get("town") or addr.get("village") or city
        # Dzielnice mają tylko miasta (klucz "city"); w mniejszych miejscowościach
        # "suburb" to zwykle osiedle, które adminowi nic nie mówi.
        district = (addr.get("city_district") or addr.get("borough") or addr.get("suburb") or "") if "city" in addr else ""
        return GeocodeResult(
            latitude=float(hit["lat"]),
            longitude=float(hit["lon"]),
            city=found_city,
            district=district,
            formatted_address=hit.get("display_name", ""),
        )


class GoogleGeocoder(Geocoder):
    name = "google"
    URL = "https://maps.googleapis.com/maps/api/geocode/json"

    def __init__(self, api_key: str, timeout: float = 10.0, viewbox: str = "") -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.viewbox = viewbox

    def geocode(self, address: str, city: str) -> GeocodeResult | None:
        query = ", ".join(p for p in (address.strip(), city.strip()) if p)
        params = {"address": query, "key": self.api_key, "language": "pl", "region": "pl"}
        if self.viewbox:
            lon1, lat1, lon2, lat2 = self.viewbox.split(",")
            params["bounds"] = f"{min(lat1, lat2)},{min(lon1, lon2)}|{max(lat1, lat2)},{max(lon1, lon2)}"
        try:
            resp = httpx.get(
                self.URL,
                params=params,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise GeocodingError(f"Google Maps: {exc}") from exc
        body = resp.json()
        if body.get("status") == "ZERO_RESULTS":
            return None
        if body.get("status") != "OK":
            raise GeocodingError(f"Google Maps: {body.get('status')} {body.get('error_message', '')}".strip())
        hit = body["results"][0]
        parts = {t: c["long_name"] for c in hit["address_components"] for t in c["types"]}
        loc = hit["geometry"]["location"]
        return GeocodeResult(
            latitude=loc["lat"],
            longitude=loc["lng"],
            city=parts.get("locality", city),
            district=parts.get("sublocality_level_1") or parts.get("sublocality", ""),
            formatted_address=hit.get("formatted_address", ""),
        )


class CachedGeocoder(Geocoder):
    """Pamięć podręczna — ten sam adres nie jest odpytywany dwa razy (limity / koszty API)."""

    def __init__(self, inner: Geocoder) -> None:
        self.inner = inner
        self.name = inner.name
        self._cache: dict[tuple[str, str], GeocodeResult | None] = {}

    def geocode(self, address: str, city: str) -> GeocodeResult | None:
        key = (address.strip().lower(), city.strip().lower())
        if key not in self._cache:
            self._cache[key] = self.inner.geocode(address, city)
        return self._cache[key]


@lru_cache
def get_geocoder() -> Geocoder:
    """Zależność FastAPI; w testach podmieniana przez ``app.dependency_overrides``."""
    cfg = get_config()
    box = cfg.geocoding_viewbox
    return CachedGeocoder(GoogleGeocoder(cfg.google_maps_api_key, viewbox=box) if cfg.google_maps_api_key else NominatimGeocoder(viewbox=box))
