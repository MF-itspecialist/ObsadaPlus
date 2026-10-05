"""Dyspozycyjność sędziów: zapis (upsert) i konwersja do obiektów domenowych."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Availability, Referee
from app.optimization.domain import AvailabilityEntry
from app.schemas.availability import AvailabilityUpsert


class AvailabilityError(ValueError):
    pass


def list_availability(
    db: Session,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    referee_id: int | None = None,
) -> list[Availability]:
    q = select(Availability).order_by(Availability.date, Availability.referee_id)
    if date_from:
        q = q.where(Availability.date >= date_from)
    if date_to:
        q = q.where(Availability.date <= date_to)
    if referee_id:
        q = q.where(Availability.referee_id == referee_id)
    return list(db.scalars(q))


def upsert(db: Session, data: AvailabilityUpsert, commit: bool = True) -> Availability:
    if db.get(Referee, data.referee_id) is None:
        raise AvailabilityError(f"Sędzia {data.referee_id} nie istnieje")
    row = db.scalar(
        select(Availability).where(
            Availability.referee_id == data.referee_id, Availability.date == data.date
        )
    )
    if row is None:
        row = Availability(referee_id=data.referee_id, date=data.date)
        db.add(row)
    row.available = data.available
    # Niedostępny → godziny bez znaczenia.
    row.available_from = data.available_from if data.available else None
    row.available_to = data.available_to if data.available else None
    if commit:
        db.commit()
        db.refresh(row)
    return row


def upsert_many(db: Session, items: list[AvailabilityUpsert]) -> list[Availability]:
    rows = [upsert(db, item, commit=False) for item in items]
    db.commit()
    return rows


def to_entry(row: Availability) -> AvailabilityEntry:
    return AvailabilityEntry(
        date=row.date,
        available=row.available,
        available_from=row.available_from,
        available_to=row.available_to,
    )


def describe(row: Availability | None) -> str:
    return to_entry(row).describe() if row else "brak zgłoszenia"
