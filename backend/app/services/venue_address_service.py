"""Uzupełnianie adresów obiektów (ulica, kod pocztowy) na podstawie ich współrzędnych."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Venue
from app.services.geocoding_service import Geocoder, GeocodingError


@dataclass
class FillReport:
    checked: int = 0
    filled: int = 0
    not_found: list[str] = field(default_factory=list)


def fill_venue_addresses(db: Session, geocoder: Geocoder, log: Callable[[str], None] = lambda _: None) -> FillReport:
    """Dla obiektów bez kodu pocztowego pyta mapę o adres w miejscu stadionu.

    Wpisany ręcznie adres i miasto zostają; uzupełniamy tylko puste pola.
    Zapisuje po każdym obiekcie, więc przerwane uzupełnianie można wznowić.
    """
    report = FillReport()
    # Kilka obiektów w tym samym punkcie = pinezka w centrum miejscowości (adres nieznany przy imporcie):
    # kod pocztowy miejscowości bierzemy, ale ulicy z centrum nie przypisujemy.
    points = Counter((round(v.latitude, 4), round(v.longitude, 4)) for v in db.scalars(select(Venue)))
    venues = list(db.scalars(select(Venue).where(Venue.postal_code == "").order_by(Venue.city, Venue.name)))
    for i, venue in enumerate(venues, 1):
        report.checked += 1
        try:
            found = geocoder.reverse(venue.latitude, venue.longitude)
        except GeocodingError as exc:
            log(f"  przerwano: usługa map niedostępna ({exc})")
            break
        if found is None or not found.postal_code:
            report.not_found.append(f"{venue.name} ({venue.city})")
            continue
        venue.postal_code = found.postal_code
        exact_pin = points[(round(venue.latitude, 4), round(venue.longitude, 4))] == 1
        if not venue.address.strip() and found.street and exact_pin:
            venue.address = found.street
        if not venue.city.strip() and found.city:
            venue.city = found.city
        db.commit()
        report.filled += 1
        log(f"  {i}/{len(venues)}  {venue.name}: {venue.address}, {venue.postal_code} {venue.city}")
    return report
