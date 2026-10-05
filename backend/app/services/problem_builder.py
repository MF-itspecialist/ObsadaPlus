"""Budowa ``Problem`` (wejście silnika optymalizacji) na podstawie bazy danych."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Assignment, Availability, GenerationMode, Match, MatchStatus, Referee
from app.optimization.domain import FixedBooking, OptimizationSettings, Problem, RefereeProfile, Slot, round_bounds
from app.services.availability_service import to_entry
from app.services.routing_service import GeoPoint


def week_bounds(date_from: dt.date, date_to: dt.date) -> tuple[dt.date, dt.date]:
    """Poszerza zakres do pełnych kolejek (limity weekendowe liczą też mecze spoza zakresu)."""
    return round_bounds(date_from)[0], round_bounds(date_to)[1]


def match_label(m: Match) -> str:
    return f"{m.home_team} – {m.away_team}"


def make_slot(m: Match, role) -> Slot:
    return Slot(
        match_id=m.id,
        role=role,
        date=m.date,
        start=dt.datetime.combine(m.date, m.start_time),
        end=dt.datetime.combine(m.date, m.estimated_end_time),
        arrival_before_minutes=m.arrival_before_minutes,
        venue=GeoPoint(m.venue.latitude, m.venue.longitude, m.venue.name),
        label=match_label(m),
        league=m.league,
    )


def referee_profile(r: Referee, availability: list[Availability]) -> RefereeProfile:
    return RefereeProfile(
        id=r.id,
        name=r.full_name,
        home=GeoPoint(r.latitude, r.longitude, r.address or r.city),
        active=r.active,
        preferred_matches_per_day=r.preferred_matches_per_day,
        max_matches_per_day=r.max_matches_per_day,
        preferred_matches_per_weekend=r.preferred_matches_per_weekend,
        max_matches_per_weekend=r.max_matches_per_weekend,
        availability={a.date: to_entry(a) for a in availability},
    )


@dataclass
class BuiltProblem:
    problem: Problem
    matches: dict[int, Match]


def build_problem(
    db: Session,
    date_from: dt.date,
    date_to: dt.date,
    settings: OptimizationSettings,
    mode: GenerationMode = GenerationMode.KEEP_MANUAL,
    keep_all_existing: bool = False,
) -> BuiltProblem:
    """Tworzy problem dla okresu [date_from, date_to].

    * sloty = wszystkie role wszystkich nieodwołanych meczów z okresu,
    * zablokowane: przypisania spoza okresu (ta sama kolejka wt–pon) oraz — w trybie
      KEEP_MANUAL — ręczne przypisania z okresu,
    * ``keep_all_existing`` = wszystkie istniejące przypisania jako zablokowane
      (ocena bieżącej obsady, ranking kandydatów przy ręcznej zmianie).
    """
    ctx_from, ctx_to = week_bounds(date_from, date_to)
    matches = list(
        db.scalars(
            select(Match)
            .options(selectinload(Match.venue), selectinload(Match.assignments))
            .where(Match.date >= ctx_from, Match.date <= ctx_to, Match.status != MatchStatus.CANCELLED)
        )
    )
    slots: list[Slot] = []
    fixed: list[FixedBooking] = []
    in_period: dict[int, Match] = {}
    for m in matches:
        inside = date_from <= m.date <= date_to
        roles = m.required_roles
        slot_by_role = {role: make_slot(m, role) for role in roles}
        if inside:
            in_period[m.id] = m
            slots.extend(slot_by_role.values())
        for a in m.assignments:
            if a.role not in slot_by_role:
                continue
            keep = (not inside) or keep_all_existing or (
                mode == GenerationMode.KEEP_MANUAL and a.manually_modified
            )
            if keep:
                fixed.append(
                    FixedBooking(
                        slot=slot_by_role[a.role],
                        referee_id=a.referee_id,
                        manually_modified=a.manually_modified,
                        in_scope=inside,
                    )
                )

    referees = list(db.scalars(select(Referee).order_by(Referee.last_name, Referee.first_name)))
    avail_rows = db.scalars(
        select(Availability).where(Availability.date >= ctx_from, Availability.date <= ctx_to)
    )
    by_ref: dict[int, list[Availability]] = {}
    for a in avail_rows:
        by_ref.setdefault(a.referee_id, []).append(a)
    profiles = [referee_profile(r, by_ref.get(r.id, [])) for r in referees]
    return BuiltProblem(Problem(slots=slots, referees=profiles, fixed=fixed, settings=settings), in_period)
