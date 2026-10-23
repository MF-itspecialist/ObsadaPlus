"""Lokalizacje stadionów z Google Maps (Places API, wyszukiwanie tekstowe).

Obiekty z importu 90minut mają często pinezkę w centrum miejscowości („Boisko: Agape
Białołęka (Warszawa)”). Szukamy w Google Maps stadionu klubu i zapisujemy jego
współrzędne, adres i kod pocztowy. Wynik dalej niż ``MAX_JUMP_KM`` od dotychczasowej
pinezki (inna miejscowość o tej samej nazwie) jest odrzucany do ręcznego sprawdzenia.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Venue

URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = "places.displayName,places.formattedAddress,places.location,places.types,places.addressComponents"
SPORT_TYPES = {"stadium", "sports_complex", "athletic_field", "sports_club", "sports_activity_location", "arena"}
MAX_JUMP_KM = 25.0
# woj. mazowieckie z zapasem
REGION_BOX = {"low": {"latitude": 51.0, "longitude": 19.2}, "high": {"latitude": 53.5, "longitude": 23.2}}
PREFIX = "Boisko: "


@dataclass
class Place:
    name: str
    latitude: float
    longitude: float
    street: str
    postal_code: str
    city: str
    is_sport: bool


@dataclass
class LookupReport:
    updated: list[str] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)
    too_far: list[str] = field(default_factory=list)


class PlacesClient:
    def __init__(self, api_key: str, timeout: float = 15.0) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def search(self, query: str) -> list[Place]:
        body = {"textQuery": query, "languageCode": "pl", "regionCode": "PL", "maxResultCount": 5,
                "locationRestriction": {"rectangle": REGION_BOX}}
        headers = {"X-Goog-Api-Key": self.api_key, "X-Goog-FieldMask": FIELDS}
        resp = httpx.post(URL, json=body, headers=headers, timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"Google Places: {resp.status_code} {resp.text[:300]}")
        return [_place(p) for p in resp.json().get("places", [])]


def _place(p: dict) -> Place:
    parts = {t: c.get("longText", "") for c in p.get("addressComponents", []) for t in c.get("types", [])}
    street = " ".join(x for x in (parts.get("route", ""), parts.get("street_number", "")) if x)
    return Place(
        name=p.get("displayName", {}).get("text", ""),
        latitude=p["location"]["latitude"],
        longitude=p["location"]["longitude"],
        street=street,
        postal_code=parts.get("postal_code", ""),
        city=parts.get("locality", ""),
        is_sport=bool(SPORT_TYPES & set(p.get("types", []))),
    )


def query_for(venue: Venue) -> str:
    """'Boisko: Agape Białołęka (Warszawa)' → 'stadion Agape Białołęka Warszawa'."""
    if venue.name.startswith(PREFIX):
        club = venue.name[len(PREFIX):].replace("(", " ").replace(")", " ")
        return " ".join(f"stadion {club}".split())
    return " ".join(f"{venue.name} {venue.address} {venue.city}".split())


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def locate_stadiums(db: Session, client: PlacesClient, log: Callable[[str], None] = lambda _: None) -> LookupReport:
    """Sprawdza w Google Maps każdy obiekt i poprawia jego lokalizację, adres i kod pocztowy."""
    report = LookupReport()
    venues = list(db.scalars(select(Venue).order_by(Venue.city, Venue.name)))
    for i, venue in enumerate(venues, 1):
        query = query_for(venue)
        places = client.search(query)
        # najpierw obiekty sportowe, potem pierwszy wynik
        place = next((p for p in places if p.is_sport), places[0] if places else None)
        if place is None:
            report.not_found.append(f"{venue.name} ({venue.city})")
            log(f"  {i}/{len(venues)}  BRAK w Google Maps: {venue.name}")
            continue
        jump = distance_km(venue.latitude, venue.longitude, place.latitude, place.longitude)
        if jump > MAX_JUMP_KM:
            report.too_far.append(f"{venue.name}: Google wskazuje „{place.name}” ({place.city}), {jump:.0f} km od obecnej pinezki")
            log(f"  {i}/{len(venues)}  POMINIĘTO (za daleko, {jump:.0f} km): {venue.name} → {place.name}, {place.city}")
            continue
        venue.latitude, venue.longitude = place.latitude, place.longitude
        if place.street:
            venue.address = place.street
        if place.postal_code:
            venue.postal_code = place.postal_code
        db.commit()
        report.updated.append(venue.name)
        log(f"  {i}/{len(venues)}  {venue.name} → {place.name}: {venue.address}, {venue.postal_code} ({jump:.1f} km)")
    return report
