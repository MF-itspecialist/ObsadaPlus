"""Pomocnicze fabryki obiektów domenowych do testów generatora."""

from __future__ import annotations

import datetime as dt
import itertools

from app.models.enums import RefereeRole
from app.optimization.domain import AvailabilityEntry, RefereeProfile, Slot
from app.services.routing_service import GeoPoint, RoutingService

SATURDAY = dt.date(2026, 10, 10)
SUNDAY = dt.date(2026, 10, 11)

# Lokalizacje w Warszawie i okolicach.
WARSZAWA = GeoPoint(52.2297, 21.0122, "Warszawa Centrum")
URSYNOW = GeoPoint(52.1500, 21.0300, "Warszawa Ursynów")
PIASECZNO = GeoPoint(52.0810, 21.0240, "Piaseczno")
LEGIONOWO = GeoPoint(52.4010, 20.9260, "Legionowo")
BIALOLEKA = GeoPoint(52.3200, 20.9750, "Białołęka")
OTWOCK = GeoPoint(52.1050, 21.2610, "Otwock")
PRUSZKOW = GeoPoint(52.1700, 20.8000, "Pruszków")
GRODZISK = GeoPoint(52.1080, 20.6250, "Grodzisk Mazowiecki")
SOCHACZEW = GeoPoint(52.2290, 20.2380, "Sochaczew")

_ids = itertools.count(1)


def referee(
    home: GeoPoint,
    *,
    id: int | None = None,
    name: str | None = None,
    days: tuple[dt.date, ...] = (SATURDAY, SUNDAY),
    available_from: str | None = None,
    available_to: str | None = None,
    available: bool = True,
    active: bool = True,
    preferred_day: int = 2,
    max_day: int = 3,
    preferred_weekend: int = 4,
    max_weekend: int = 5,
) -> RefereeProfile:
    rid = id if id is not None else next(_ids)
    t = lambda s: dt.time.fromisoformat(s) if s else None  # noqa: E731
    return RefereeProfile(
        id=rid,
        name=name or f"Sędzia {rid}",
        home=home,
        active=active,
        preferred_matches_per_day=preferred_day,
        max_matches_per_day=max_day,
        preferred_matches_per_weekend=preferred_weekend,
        max_matches_per_weekend=max_weekend,
        availability={
            d: AvailabilityEntry(d, available, t(available_from), t(available_to)) for d in days
        },
    )


def slot(
    match_id: int,
    venue: GeoPoint,
    start: str,
    end: str,
    *,
    day: dt.date = SATURDAY,
    arrival_before: int = 45,
    role: RefereeRole = RefereeRole.MAIN,
) -> Slot:
    return Slot(
        match_id=match_id,
        role=role,
        date=day,
        start=dt.datetime.combine(day, dt.time.fromisoformat(start)),
        end=dt.datetime.combine(day, dt.time.fromisoformat(end)),
        arrival_before_minutes=arrival_before,
        venue=venue,
        label=f"Mecz {match_id} ({venue.label})",
    )


class FixedTimeRouting(RoutingService):
    """Routing o stałym czasie i odległości — do testów arytmetyki czasu dojazdu."""

    name = "fixed"

    def __init__(self, minutes: float, km: float = 10.0) -> None:
        self.minutes = minutes
        self.km = km

    def get_distance(self, origin: GeoPoint, destination: GeoPoint) -> float:
        return 0.0 if origin == destination else self.km

    def get_travel_time(self, origin: GeoPoint, destination: GeoPoint) -> float:
        return 0.0 if origin == destination else self.minutes
