"""Wczytanie przykładowych danych (10 obiektów, 12 sędziów, 24 mecze, dyspozycyjność)."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import seed_data as data
from app.models import Availability, Match, MatchStatus, Referee, Venue


def _t(value: str) -> dt.time:
    return dt.time.fromisoformat(value)


def seed_database(db: Session, force: bool = False) -> bool:
    """Wypełnia pustą bazę danymi testowymi. Zwraca False, gdy dane już istnieją."""
    if not force and db.scalar(select(func.count(Referee.id))):
        return False

    venues = [Venue(**v) for v in data.VENUES]
    db.add_all(venues)

    referees: dict[str, Referee] = {}
    for first, last, city, district, address, lat, lng, licenses, active, pd, md, pw, mw in data.REFEREES:
        referees[last] = Referee(
            first_name=first,
            last_name=last,
            city=city,
            district=district,
            address=address,
            latitude=lat,
            longitude=lng,
            licenses=licenses,
            active=active,
            preferred_matches_per_day=pd,
            max_matches_per_day=md,
            preferred_matches_per_weekend=pw,
            max_matches_per_weekend=mw,
        )
    db.add_all(referees.values())
    db.flush()

    for last, days in data.AVAILABILITY.items():
        for day, value in days.items():
            entry = Availability(referee_id=referees[last].id, date=dt.date.fromisoformat(day))
            if value is False:
                entry.available = False
            elif value is None:
                entry.available = True
            else:
                entry.available = True
                entry.available_from, entry.available_to = _t(value[0]), _t(value[1])
            db.add(entry)

    for ext, day, start, end, league, home, away, venue_idx, arrival in data.MATCHES:
        db.add(
            Match(
                external_id=ext,
                date=dt.date.fromisoformat(day),
                start_time=_t(start),
                estimated_end_time=_t(end),
                league=league,
                home_team=home,
                away_team=away,
                venue_id=venues[venue_idx].id,
                required_referees=1,
                arrival_before_minutes=arrival,
                status=MatchStatus.UNASSIGNED,
            )
        )
    db.commit()
    return True


if __name__ == "__main__":
    from app.database.db import SessionLocal

    with SessionLocal() as session:
        print("Wczytano dane testowe." if seed_database(session) else "Baza zawiera już dane — pominięto.")
