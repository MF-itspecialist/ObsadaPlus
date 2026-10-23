"""Publikacja obsady: zamrożenie bieżącego stanu okresu jako kolejnej wersji."""

from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Publication
from app.services import export_service


def publish(db: Session, date_from: dt.date, date_to: dt.date) -> Publication:
    previous = db.scalar(
        select(func.max(Publication.version)).where(Publication.date_from == date_from, Publication.date_to == date_to)
    )
    pub = Publication(
        date_from=date_from,
        date_to=date_to,
        version=(previous or 0) + 1,
        published_at=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None, microsecond=0),
        rows=export_service.collect(db, date_from, date_to),
    )
    db.add(pub)
    db.commit()
    db.refresh(pub)
    return pub


def latest(db: Session, date_from: dt.date, date_to: dt.date) -> Publication | None:
    return db.scalar(
        select(Publication)
        .where(Publication.date_from == date_from, Publication.date_to == date_to)
        .order_by(Publication.version.desc())
        .limit(1)
    )


def local_time(pub: Publication) -> dt.datetime:
    """Czas publikacji w strefie polskiej (w bazie trzymany jako UTC)."""
    return pub.published_at.replace(tzinfo=dt.timezone.utc).astimezone(ZoneInfo("Europe/Warsaw"))


def summary(db: Session, pub: Publication, with_rows: bool = False) -> dict[str, Any]:
    current = export_service.collect(db, pub.date_from, pub.date_to)
    data = {
        "id": pub.id,
        "date_from": pub.date_from,
        "date_to": pub.date_to,
        "version": pub.version,
        "published_at": pub.published_at.replace(tzinfo=dt.timezone.utc),
        "match_count": len(pub.rows),
        "changed_matches": export_service.changed_matches(pub.rows, current),
    }
    if with_rows:
        data["rows"] = pub.rows
    return data
