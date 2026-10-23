"""Panel sędziego: jego opublikowane mecze i własna dyspozycyjność."""

from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Availability, Publication
from app.schemas.availability import AvailabilityUpsert, OwnAvailabilitySave
from app.services import availability_service
from app.services.export_service import ROLE_LABELS

# Jak daleko w przód sędzia może zgłaszać dyspozycyjność.
MAX_DAYS_AHEAD = 120


class PanelError(ValueError):
    pass


def today() -> dt.date:
    return dt.datetime.now(ZoneInfo("Europe/Warsaw")).date()


def published_matches(db: Session, referee_id: int, from_date: dt.date | None = None) -> list[dict[str, Any]]:
    """Mecze sędziego z najnowszych publikacji (to, co ogłoszono — nie robocza obsada)."""
    from_date = from_date or today()
    pubs = db.scalars(
        select(Publication).where(Publication.date_to >= from_date).order_by(Publication.published_at, Publication.id)
    )
    latest: dict[tuple[dt.date, dt.date], Publication] = {}
    for pub in pubs:
        latest[(pub.date_from, pub.date_to)] = pub  # rosnąco — zostaje najnowsza wersja okresu
    by_match: dict[int, dict[str, Any]] = {}
    for pub in sorted(latest.values(), key=lambda p: (p.published_at, p.id)):
        for row in pub.rows:
            if dt.date.fromisoformat(row["date"]) < from_date:
                continue
            mine = next((c for c in row["crew"] if c["referee_id"] == referee_id), None)
            if mine is None:
                by_match.pop(row["match_id"], None)  # nowsza publikacja zdjęła sędziego z meczu
                continue
            by_match[row["match_id"]] = {
                "match_id": row["match_id"],
                "date": row["date"],
                "start_time": row["start_time"],
                "league": row["league"],
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "venue_name": row["venue_name"],
                "venue_address": row["venue_address"],
                "cancelled": row["cancelled"],
                "role": mine["role"],
                "role_label": ROLE_LABELS.get(mine["role"], mine["role"]),
                "distance_km": mine["distance_km"],
                "crew": [
                    {"role": c["role"], "role_label": ROLE_LABELS.get(c["role"], c["role"]), "referee_name": c["referee_name"]}
                    for c in row["crew"]
                    if c["referee_id"] != referee_id
                ],
                "version": pub.version,
                "published_at": pub.published_at.replace(tzinfo=dt.timezone.utc),
            }
    return sorted(by_match.values(), key=lambda m: (m["date"], m["start_time"]))


def own_availability(db: Session, referee_id: int, date_from: dt.date, date_to: dt.date) -> list[Availability]:
    return availability_service.list_availability(db, date_from, date_to, referee_id)


def save_own_availability(db: Session, referee_id: int, data: OwnAvailabilitySave) -> list[Availability]:
    first, last = today() + dt.timedelta(days=1), today() + dt.timedelta(days=MAX_DAYS_AHEAD)
    days = [i.date for i in data.items] + list(data.cleared)
    if len(set(days)) != len(days):
        raise PanelError("Każdy dzień można podać tylko raz")
    for d in days:
        if d < first:
            raise PanelError(f"Dyspozycyjność na {d:%d.%m.%Y} nie może być już zmieniona — zgłoś ją obsadzającemu")
        if d > last:
            raise PanelError(f"Można zgłaszać najwyżej {MAX_DAYS_AHEAD} dni naprzód")
    rows = [
        availability_service.upsert(db, AvailabilityUpsert(referee_id=referee_id, **item.model_dump()), commit=False, by_referee=True)
        for item in data.items
    ]
    if data.cleared:
        db.execute(delete(Availability).where(Availability.referee_id == referee_id, Availability.date.in_(data.cleared)))
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows
