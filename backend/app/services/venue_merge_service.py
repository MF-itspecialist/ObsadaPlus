"""Wspólny obiekt dla drużyn jednego klubu (Agape i Agape II grają na tym samym boisku)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importers.m90_importer import club_name
from app.models import Venue

PREFIX = "Boisko: "


@dataclass
class MergeReport:
    merged: list[str] = field(default_factory=list)  # „Boisko: Agape II … → Boisko: Agape …”
    renamed: list[str] = field(default_factory=list)


def merge_reserve_venues(db: Session) -> MergeReport:
    """Obiekty „Boisko: <drużyna rezerw>” łączy z obiektem pierwszej drużyny klubu.

    Mecze przechodzą na obiekt klubu; gdy klub nie ma jeszcze obiektu, obiekt rezerw
    dostaje nazwę klubu. Obiekty z nazwą stadionu (np. „Stadion Hutnika”) zostają bez zmian.
    """
    report = MergeReport()
    venues = list(db.scalars(select(Venue).where(Venue.name.startswith(PREFIX)).order_by(Venue.id)))
    by_name = {v.name: v for v in venues}
    for venue in venues:
        target_name = PREFIX + club_name(venue.name[len(PREFIX):])
        if target_name == venue.name:
            continue
        target = by_name.get(target_name)
        if target is None:
            report.renamed.append(f"{venue.name} → {target_name}")
            del by_name[venue.name]
            venue.name = target_name
            by_name[target_name] = venue
            continue
        for match in list(venue.matches):
            match.venue = target
        db.flush()
        report.merged.append(f"{venue.name} → {target_name}")
        del by_name[venue.name]
        db.delete(venue)
    db.commit()
    return report
