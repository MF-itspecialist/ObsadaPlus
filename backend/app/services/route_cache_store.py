"""Trwała pamięć tras w bazie — każdą parę punktów pytamy Google/OSRM tylko raz."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.models import RouteCacheEntry
from app.services.routing_service import CacheKey, RouteInfo, RouteStore


class DbRouteStore(RouteStore):
    def __init__(self, db: Session) -> None:
        self.db = db

    def load(self, provider: str, keys: Iterable[CacheKey]) -> dict[CacheKey, RouteInfo]:
        keys = list(keys)
        found: dict[CacheKey, RouteInfo] = {}
        for i in range(0, len(keys), 500):
            chunk = keys[i : i + 500]
            rows = self.db.scalars(
                select(RouteCacheEntry).where(
                    RouteCacheEntry.provider == provider,
                    tuple_(
                        RouteCacheEntry.origin_lat, RouteCacheEntry.origin_lon,
                        RouteCacheEntry.dest_lat, RouteCacheEntry.dest_lon,
                    ).in_([(o[0], o[1], d[0], d[1]) for o, d in chunk]),
                )
            )
            for r in rows:
                key = ((r.origin_lat, r.origin_lon), (r.dest_lat, r.dest_lon))
                found[key] = RouteInfo(r.distance_km, r.travel_minutes, provider)
        return found

    def save(self, provider: str, routes: dict[CacheKey, RouteInfo]) -> None:
        if not routes:
            return
        existing = self.load(provider, routes.keys())
        for (o, d), info in routes.items():
            if (o, d) in existing:
                continue
            self.db.add(RouteCacheEntry(
                provider=provider, origin_lat=o[0], origin_lon=o[1], dest_lat=d[0], dest_lon=d[1],
                distance_km=info.distance_km, travel_minutes=info.travel_minutes,
            ))
        self.db.commit()
