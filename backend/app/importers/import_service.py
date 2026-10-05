"""Zapis zaimportowanych meczów: upsert po external_id, rozwiązywanie obiektów."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.importers.base import MatchImporter, MatchImportRecord
from app.models import Match, Venue


class UnknownVenueError(ValueError):
    pass


def _resolve_venue(db: Session, r: MatchImportRecord) -> Venue:
    if r.venue_id is not None:
        venue = db.get(Venue, r.venue_id)
        if venue is None:
            raise ValueError(f"obiekt {r.venue_id} nie istnieje")
        return venue
    venue = db.scalar(select(Venue).where(func.lower(Venue.name) == (r.venue_name or "").lower()))
    if venue is not None:
        return venue
    if r.venue_latitude is None or r.venue_longitude is None:
        raise UnknownVenueError(f"nieznany obiekt '{r.venue_name}' — podaj venue_latitude i venue_longitude")
    venue = Venue(
        name=r.venue_name,
        city=r.venue_city or "",
        address=r.venue_address or "",
        latitude=r.venue_latitude,
        longitude=r.venue_longitude,
    )
    db.add(venue)
    db.flush()
    return venue


def import_matches(db: Session, importer: MatchImporter, default_duration_minutes: int = 105) -> dict:
    created = updated = 0
    errors: list[str] = []
    # Nieznane obiekty zgłaszamy raz na obiekt (import z LNP potrafi mieć wiele meczów na tym samym boisku).
    unknown_venues: dict[str, int] = {}
    for i, r in enumerate(importer.fetch_matches(), start=1):
        try:
            venue = _resolve_venue(db, r)
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
    db.commit()
    errors += [
        f"Nieznany obiekt '{name}' ({count} mecz.): dodaj go w zakładce Obiekty i zaimportuj plik ponownie"
        for name, count in unknown_venues.items()
    ]
    errors += getattr(importer, "warnings", [])
    return {"created": created, "updated": updated, "errors": errors}
