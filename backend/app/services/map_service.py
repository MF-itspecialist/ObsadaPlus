"""Dane do mapy: obiekty z meczami okresu i trasy sędziów dzień po dniu.

Trasa dnia to dom → mecz 1 → … → dom (jak w kilometrówce). Kształt drogi na mapie
daje OSRM (``/route``); bez OSRM albo przy jego awarii rysowana jest linia prosta.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from functools import lru_cache
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_config
from app.models import Match, MatchStatus
from app.services.mileage_service import _assignments, _day_route
from app.services.routing_service import GeoPoint
from app.services.settings_service import get_settings, routing_for

MAX_POINTS = 25


def _point(lat: float, lng: float) -> list[float]:
    return [round(lat, 6), round(lng, 6)]


def period_map(db: Session, date_from: dt.date, date_to: dt.date) -> dict[str, Any]:
    matches = list(
        db.scalars(
            select(Match)
            .options(selectinload(Match.venue), selectinload(Match.assignments))
            .where(Match.date >= date_from, Match.date <= date_to, Match.status != MatchStatus.CANCELLED)
            .order_by(Match.date, Match.start_time)
        )
    )
    venues: dict[int, dict[str, Any]] = {}
    for m in matches:
        v = venues.setdefault(
            m.venue_id,
            {"id": m.venue_id, "name": m.venue.name, "city": m.venue.city, "point": _point(m.venue.latitude, m.venue.longitude), "matches": []},
        )
        required = set(m.required_roles)
        filled = len({a.role for a in m.assignments} & required)
        v["matches"].append(
            {
                "id": m.id,
                "date": m.date,
                "time": f"{m.start_time:%H:%M}",
                "league": m.league,
                "home_team": m.home_team,
                "away_team": m.away_team,
                "required": len(required),
                "filled": filled,
            }
        )

    routing = routing_for(get_settings(db), db)
    by_day: dict[tuple[int, dt.date], list] = defaultdict(list)
    for a in _assignments(db, date_from, date_to):
        by_day[(a.referee_id, a.match.date)].append(a)
    referees: dict[int, dict[str, Any]] = {}
    for (rid, day), items in sorted(by_day.items(), key=lambda kv: kv[0][1]):
        ref = items[0].referee
        entry = referees.setdefault(
            rid,
            {
                "referee_id": rid,
                "name": ref.full_name,
                "location": ref.location_label,
                "home": _point(ref.latitude, ref.longitude),
                "days": [],
            },
        )
        home = GeoPoint(ref.latitude, ref.longitude, ref.address or ref.city)
        stops = [GeoPoint(a.match.venue.latitude, a.match.venue.longitude, a.match.venue.name) for a in items]
        legs = _day_route(routing, home, stops)
        entry["days"].append(
            {
                "date": day,
                "km": round(sum(legs), 1),
                "stops": [
                    {
                        "match_id": a.match_id,
                        "venue_id": a.match.venue_id,
                        "venue": a.match.venue.name,
                        "point": _point(a.match.venue.latitude, a.match.venue.longitude),
                        "time": f"{a.match.start_time:%H:%M}",
                        "role": a.role.value,
                        "label": f"{a.match.home_team} – {a.match.away_team}",
                    }
                    for a in items
                ],
            }
        )
    return {
        "date_from": date_from,
        "date_to": date_to,
        "venues": list(venues.values()),
        "referees": sorted(referees.values(), key=lambda r: r["name"]),
    }


def route_shape(points: list[tuple[float, float]]) -> dict[str, Any]:
    """Kształt trasy przez kolejne punkty (lat, lng). ``exact=False`` = linia prosta."""
    points = points[:MAX_POINTS]
    if len(points) < 2:
        return {"path": [list(p) for p in points], "exact": False}
    path = _osrm_shape(tuple(points), get_config().osrm_url)
    if path is None:
        return {"path": [list(p) for p in points], "exact": False}
    return {"path": path, "exact": True}


@lru_cache(maxsize=512)
def _osrm_shape(points: tuple[tuple[float, float], ...], osrm_url: str) -> list[list[float]] | None:
    if not osrm_url:
        return None
    coords = ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in points)
    try:
        resp = httpx.get(
            f"{osrm_url.rstrip('/')}/route/v1/driving/{coords}",
            params={"overview": "full", "geometries": "geojson"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok":
            return None
        return [_point(lat, lng) for lng, lat in data["routes"][0]["geometry"]["coordinates"]]
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        return None
