"""Uzupełnianie lokalizacji sędziów i obiektów na podstawie adresu."""

from __future__ import annotations

from fastapi import HTTPException

from app.models import Referee, Venue
from app.schemas.referee import RefereeInput
from app.schemas.venue import VenueInput
from app.services.geocoding_service import Geocoder, GeocodingError


def apply_location(obj: Referee | Venue, data: RefereeInput | VenueInput, geocoder: Geocoder) -> None:
    """Ustawia współrzędne (i dzielnicę sędziego) na obiekcie.

    * współrzędne podane jawnie (import, API) — zapisujemy je bez geokodowania,
    * nowy rekord (brak współrzędnych) lub zmieniony adres — pytamy geokoder,
    * adres bez zmian — zostawiamy zapisaną lokalizację.

    Na istniejącym rekordzie wywoływać przed nadpisaniem ``address`` / ``city``.
    """
    has_district = isinstance(obj, Referee)
    if data.latitude is not None and data.longitude is not None:
        obj.latitude, obj.longitude = data.latitude, data.longitude
        if has_district:
            obj.district = data.district or ""
        return

    unchanged = obj.latitude is not None and (obj.address, obj.city) == (data.address, data.city)
    if unchanged:
        return

    if not data.address.strip() and not data.city.strip():
        raise HTTPException(422, "Podaj adres lub miasto — na tej podstawie liczone są dojazdy")
    try:
        found = geocoder.geocode(data.address, data.city)
    except GeocodingError as exc:
        raise HTTPException(503, "Usługa map jest chwilowo niedostępna — spróbuj ponownie za chwilę") from exc
    if found is None:
        raise HTTPException(422, f"Nie znaleziono adresu „{', '.join(p for p in (data.address, data.city) if p)}” — sprawdź pisownię")
    obj.latitude, obj.longitude = found.latitude, found.longitude
    if has_district:
        obj.district = found.district
    elif not data.postal_code:
        obj.postal_code = found.postal_code
