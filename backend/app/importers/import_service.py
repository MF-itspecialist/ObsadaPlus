"""Zapis zaimportowanych meczów: upsert po external_id, rozwiązywanie obiektów."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.importers.base import MatchImporter, MatchImportRecord
from app.models import Match, Venue
from app.services.geocoding_service import Geocoder, GeocodingError
from app.services.observer_service import auto_observer, set_observer
from app.services.settings_service import get_settings


class UnknownVenueError(ValueError):
    pass


def _resolve_venue(db: Session, r: MatchImportRecord, geocoder: Geocoder | None = None) -> Venue:
    if r.venue_id is not None:
        venue = db.get(Venue, r.venue_id)
        if venue is None:
            raise ValueError(f"obiekt {r.venue_id} nie istnieje")
        return venue
    name = r.venue_name or ""
    # Najpierw dokładna nazwa: lower() w SQLite nie zna polskich liter (Ś, Ł…), więc samo porównanie
    # bez wielkości liter tworzyłoby duplikaty obiektów przy każdym meczu.
    venue = db.scalar(select(Venue).where(Venue.name == name)) or db.scalar(
        select(Venue).where(func.lower(Venue.name) == name.lower())
    )
    if venue is not None:
        return venue
    lat, lng = r.venue_latitude, r.venue_longitude
    if (lat is None or lng is None) and geocoder is not None and (r.venue_address or r.venue_city):
        # Nowy obiekt z adresem — lokalizację pobieramy z mapy, tak jak w formularzu.
        try:
            found = geocoder.geocode(r.venue_address or "", r.venue_city or "")
            if found is None and r.venue_address and r.venue_city:
                # Ulica nieznana mapie (np. w dopełniaczu „przy ul. Łabiszyńskiej”) — środek miejscowości.
                found = geocoder.geocode("", r.venue_city)
        except GeocodingError:
            found = None
        if found is not None:
            lat, lng = found.latitude, found.longitude
    if lat is None or lng is None:
        raise UnknownVenueError(f"nieznany obiekt '{r.venue_name}' — nie udało się ustalić jego lokalizacji")
    venue = Venue(
        name=r.venue_name,
        city=r.venue_city or "",
        address=r.venue_address or "",
        latitude=lat,
        longitude=lng,
    )
    db.add(venue)
    db.flush()
    return venue


def import_matches(
    db: Session, importer: MatchImporter, default_duration_minutes: int = 105, geocoder: Geocoder | None = None
) -> dict:
    created = updated = 0
    errors: list[str] = []
    observer_levels = get_settings(db).observer_levels
    # Nieznane obiekty zgłaszamy raz na obiekt (import z LNP potrafi mieć wiele meczów na tym samym boisku).
    unknown_venues: dict[str, int] = {}
    for i, r in enumerate(importer.fetch_matches(), start=1):
        try:
            venue = _resolve_venue(db, r, geocoder)
        except UnknownVenueError:
            label = f"{r.venue_name}, {r.venue_city}" if r.venue_city else r.venue_name
            unknown_venues[label] = unknown_venues.get(label, 0) + 1
            continue
        except ValueError as exc:
            errors.append(f"Rekord {i} ({r.home_team} – {r.away_team}): {exc}")
            continue
        end = r.estimated_end_time or (
            dt.datetime.combine(r.date, r.start_time) + dt.timedelta(minutes=default_duration_minutes)
        ).time()
        match = db.scalar(select(Match).where(Match.external_id == r.external_id)) if r.external_id else None
        if match is None:
            match = Match(external_id=r.external_id)
            db.add(match)
            created += 1
        else:
            updated += 1
        match.date = r.date
        match.start_time = r.start_time
        match.estimated_end_time = end
        match.league = r.league
        match.home_team = r.home_team
        match.away_team = r.away_team
        match.venue_id = venue.id
        match.required_referees = r.required_referees
        match.arrival_before_minutes = r.arrival_before_minutes
        want_observer = auto_observer(r.league, observer_levels)
        if not match.observer_manual and bool(match.observer_required) != want_observer:
            set_observer(match, want_observer)
    db.commit()
    errors += [
        f"Nie znaleziono adresu obiektu '{name}' ({count} mecz.): dodaj go w zakładce Obiekty i zaimportuj plik ponownie"
        for name, count in unknown_venues.items()
    ]
    errors += getattr(importer, "warnings", [])
    return {"created": created, "updated": updated, "errors": errors}
