"""Statystyki dla dashboardu i widoku sędziów."""

from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Assignment, Availability, Match, Referee
from app.services import scoring_service
from app.services.availability_service import describe


def dashboard(db: Session, date_from: dt.date, date_to: dt.date) -> dict[str, Any]:
    result, _ = scoring_service.evaluate_current(db, date_from, date_to)
    s = result.stats
    available_referees = len(
        set(
            db.scalars(
                select(Availability.referee_id)
                .join(Referee)
                .where(
                    Availability.date >= date_from,
                    Availability.date <= date_to,
                    Availability.available.is_(True),
                    Referee.active.is_(True),
                )
            )
        )
    )
    return {
        "date_from": date_from,
        "date_to": date_to,
        "matches_total": s.matches_total,
        "matches_assigned": s.matches_assigned,
        "matches_unassigned": s.matches_unassigned,
        "available_referees": available_referees,
        "active_referees": s.active_referees,
        "avg_matches_per_referee": s.avg_matches_per_referee,
        "total_distance_km": s.total_distance_km,
        "avg_distance_km": s.avg_distance_km,
        "conflicts": s.conflicts,
    }


def referee_overview(db: Session, date_from: dt.date, date_to: dt.date) -> list[dict[str, Any]]:
    days = [date_from + dt.timedelta(days=i) for i in range((date_to - date_from).days + 1)]
    referees = list(db.scalars(select(Referee).order_by(Referee.last_name, Referee.first_name)))
    avail = {
        (a.referee_id, a.date): a
        for a in db.scalars(
            select(Availability).where(Availability.date >= date_from, Availability.date <= date_to)
        )
    }
    counts = Counter(
        db.execute(
            select(Assignment.referee_id, Match.date)
            .join(Match)
            .where(Match.date >= date_from, Match.date <= date_to)
        ).all()
    )
    rows = []
    for r in referees:
        day_rows = [
            {"date": d, "availability": describe(avail.get((r.id, d))), "matches": counts.get((r.id, d), 0)}
            for d in days
        ]
        rows.append(
            {"referee": r, "days": day_rows, "matches_in_period": sum(x["matches"] for x in day_rows)}
        )
    return rows
