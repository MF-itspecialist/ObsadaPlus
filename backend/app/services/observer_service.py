"""Obserwatorzy: które mecze mają rolę O.

Liga z listy ``observer_levels`` w Ustawieniach → obserwator z automatu. Obsadzający może
to zmienić przy meczu (``observer_manual``) i wtedy ustawienia już tego meczu nie ruszają.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Match, MatchStatus, RefereeRole
from app.optimization.licenses import level_name


def auto_observer(league: str, levels: Iterable[str]) -> bool:
    return level_name(league) in set(levels)


def set_observer(match: Match, required: bool) -> None:
    """Włącza / wyłącza rolę O; wyłączenie usuwa przypisanego obserwatora."""
    match.observer_required = required
    if not required:
        for a in [a for a in match.assignments if a.role == RefereeRole.OBSERVER]:
            match.assignments.remove(a)
    match.refresh_status()


def apply_levels(db: Session, levels: list[str], today: dt.date | None = None) -> int:
    """Przelicza obserwatora dla przyszłych meczów bez ręcznego ustawienia. Zwraca liczbę zmian."""
    today = today or dt.date.today()
    changed = 0
    matches = db.scalars(
        select(Match)
        .options(selectinload(Match.assignments))
        .where(Match.date >= today, Match.observer_manual.is_(False), Match.status != MatchStatus.CANCELLED)
    )
    for m in matches:
        want = auto_observer(m.league, levels)
        if m.observer_required != want:
            set_observer(m, want)
            changed += 1
    db.commit()
    return changed
