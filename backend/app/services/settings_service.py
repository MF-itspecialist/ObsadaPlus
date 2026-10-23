"""Ustawienia systemu przechowywane w tabeli ``system_settings``."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_config
from app.models import SystemSetting
from app.optimization.domain import OptimizationSettings
from app.schemas.settings import SystemSettings
from app.services.routing_service import RoutingService, get_routing_service


def get_settings(db: Session) -> SystemSettings:
    """Wartości domyślne nadpisane tym, co zapisano w bazie."""
    stored = {s.key: s.value for s in db.scalars(select(SystemSetting))}
    known = {k: v for k, v in stored.items() if k in SystemSettings.model_fields}
    return SystemSettings(**known)


def update_settings(db: Session, new: SystemSettings) -> SystemSettings:
    for key, value in new.model_dump(mode="json").items():
        row = db.get(SystemSetting, key)
        if row is None:
            db.add(SystemSetting(key=key, value=value))
        else:
            row.value = value
    db.commit()
    return get_settings(db)


def to_optimization_settings(s: SystemSettings) -> OptimizationSettings:
    brackets = tuple((float(u), float(p)) for u, p in sorted(s.distance_brackets))
    if brackets:
        # ostatni próg obejmuje wszystkie większe odległości
        brackets = brackets[:-1] + ((float("inf"), brackets[-1][1]),)
    return OptimizationSettings(
        transport_safety_buffer_minutes=s.transport_safety_buffer_minutes,
        distance_weight=s.distance_weight,
        travel_time_weight=s.travel_time_weight,
        daily_match_weight=s.daily_match_weight,
        weekend_match_weight=s.weekend_match_weight,
        workload_balance_weight=s.workload_balance_weight,
        distance_brackets=brackets or OptimizationSettings().distance_brackets,
        within_preferred_factor=s.within_preferred_factor,
        over_preferred_factor=s.over_preferred_factor,
        assume_available_without_entry=s.assume_available_without_entry,
        arrival_before_minutes=s.arrival_before_minutes,
        women_priority_penalty=s.women_priority_penalty,
        crew_route_weight=s.crew_route_weight,
    )


def routing_for(s: SystemSettings, db: Session | None = None) -> RoutingService:
    """Serwis tras wg konfiguracji; z ``db`` trasy z Google/OSRM są zapamiętywane w bazie."""
    from app.services.route_cache_store import DbRouteStore

    cfg = get_config()
    return get_routing_service(
        cfg.routing_provider,
        road_factor=s.routing_road_factor,
        avg_speed_kmh=s.routing_avg_speed_kmh,
        google_api_key=cfg.google_maps_api_key,
        osrm_url=cfg.osrm_url,
        store=DbRouteStore(db) if db is not None else None,
    )
