"""Generowanie obsady (podgląd → zatwierdzenie) oraz ręczne zmiany przypisań."""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Assignment,
    GenerationMode,
    GenerationRun,
    GenerationRunStatus,
    Match,
    MatchStatus,
    Referee,
    RefereeRole,
)
from app.optimization.generator import AssignmentGenerator, GenerationResult
from app.optimization.domain import Slot, fmt_time
from app.schemas.optimization import GenerateRequest
from app.services import scoring_service
from app.services.problem_builder import build_problem
from app.services.settings_service import get_settings, routing_for, to_optimization_settings


class AssignmentError(ValueError):
    """Błąd biznesowy (np. nieistniejący mecz) — API zamienia go na 4xx."""


# --- serializacja wyniku generatora ------------------------------------------
def _match_info(slot: Slot, match: Match | None) -> dict[str, Any]:
    return {
        "match_id": slot.match_id,
        "date": slot.date.isoformat(),
        "start_time": fmt_time(slot.start),
        "end_time": fmt_time(slot.end),
        "league": slot.league,
        "home_team": match.home_team if match else slot.label,
        "away_team": match.away_team if match else "",
        "venue_name": slot.venue.label,
    }


def serialize_result(result: GenerationResult, matches: dict[int, Match]) -> dict[str, Any]:
    return {
        "assignments": [
            {
                "match": _match_info(a.slot, matches.get(a.slot.match_id)),
                "role": a.slot.role.value,
                "referee_id": a.referee_id,
                "referee_name": a.referee_name,
                "score": a.score,
                "distance_km": a.distance_km,
                "travel_minutes": a.travel_minutes,
                "manually_modified": a.manually_modified,
                "explanation": a.explanation,
                "conflict": a.conflict,
            }
            for a in result.assignments
        ],
        "unassigned": [
            {
                "match": _match_info(u.slot, matches.get(u.slot.match_id)),
                "role": u.slot.role.value,
                "reasons": [asdict(r) for r in u.reasons],
                "rejected_examples": u.rejected_examples,
            }
            for u in result.unassigned
        ],
    }


def referee_info(db: Session, referee_ids: set[int]) -> dict[int, dict[str, str]]:
    """Licencje i miejsce zamieszkania sędziów — to, co admin widzi przy obsadzie."""
    if not referee_ids:
        return {}
    refs = db.scalars(select(Referee).where(Referee.id.in_(referee_ids)))
    return {
        r.id: {"referee_licenses": r.licenses or [], "referee_location": r.location_label} for r in refs
    }


def run_to_preview(db: Session, run: GenerationRun) -> dict[str, Any]:
    info = referee_info(db, {a["referee_id"] for a in run.result["assignments"]})
    return {
        "run_id": run.id,
        "status": run.status,
        "params": run.params,
        "stats": run.stats,
        **run.result,
        "assignments": [{**a, **info.get(a["referee_id"], {})} for a in run.result["assignments"]],
    }


# --- generowanie ---------------------------------------------------------------
def generate_preview(db: Session, req: GenerateRequest) -> GenerationRun:
    """Uruchamia generator i zapisuje propozycję (status PREVIEW). Nie zmienia obsady."""
    s = get_settings(db)
    built = build_problem(
        db,
        req.date_from,
        req.date_to,
        to_optimization_settings(s),
        mode=req.mode,
        daily_cap=s.generator_max_matches_per_day,
    )
    result = AssignmentGenerator(routing_for(s, db)).generate_assignments(built.problem)
    _discard_previews(db, req.date_from, req.date_to)
    run = GenerationRun(
        status=GenerationRunStatus.PREVIEW,
        params=req.model_dump(mode="json"),
        result=serialize_result(result, built.matches),
        stats=asdict(result.stats),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _same_period(run: GenerationRun, date_from: dt.date, date_to: dt.date) -> bool:
    return run.params.get("date_from") == date_from.isoformat() and run.params.get("date_to") == date_to.isoformat()


def _discard_previews(db: Session, date_from: dt.date, date_to: dt.date) -> None:
    """Starsze niezatwierdzone podglądy tego okresu przestają być aktualne."""
    for run in db.scalars(select(GenerationRun).where(GenerationRun.status == GenerationRunStatus.PREVIEW)):
        if _same_period(run, date_from, date_to):
            run.status = GenerationRunStatus.DISCARDED


def pending_preview(db: Session, date_from: dt.date, date_to: dt.date) -> GenerationRun | None:
    """Ostatni niezatwierdzony podgląd okresu — żeby przetrwał odświeżenie strony."""
    runs = db.scalars(
        select(GenerationRun)
        .where(GenerationRun.status == GenerationRunStatus.PREVIEW)
        .order_by(GenerationRun.id.desc())
    )
    return next((r for r in runs if _same_period(r, date_from, date_to)), None)


def discard(db: Session, run_id: int) -> None:
    run = db.get(GenerationRun, run_id)
    if run is None:
        raise AssignmentError(f"Brak generowania o id {run_id}")
    if run.status == GenerationRunStatus.PREVIEW:
        run.status = GenerationRunStatus.DISCARDED
        db.commit()


def confirm(db: Session, run_id: int) -> dict[str, Any]:
    """Zapisuje propozycję jako obsadę.

    Usuwa automatyczne przypisania z okresu (w trybie FULL także ręczne),
    a następnie zapisuje przypisania z propozycji. Ręczne przypisania dodane
    po wygenerowaniu podglądu mają pierwszeństwo — kolidujące propozycje są pomijane.
    """
    run = db.get(GenerationRun, run_id)
    if run is None:
        raise AssignmentError(f"Brak generowania o id {run_id}")
    if run.status != GenerationRunStatus.PREVIEW:
        raise AssignmentError(f"Generowanie {run_id} ma status {run.status.value} — nie można zatwierdzić")

    date_from = dt.date.fromisoformat(run.params["date_from"])
    date_to = dt.date.fromisoformat(run.params["date_to"])
    mode = GenerationMode(run.params["mode"])
    matches = {
        m.id: m
        for m in db.scalars(
            select(Match)
            .options(selectinload(Match.assignments))
            .where(Match.date >= date_from, Match.date <= date_to)
        )
    }
    run_started = run.created_at
    for m in matches.values():
        for a in list(m.assignments):
            # ręczne zmiany wykonane po podglądzie zostają zawsze
            changed_after = a.manually_modified and a.updated_at and run_started and a.updated_at > run_started
            if (mode == GenerationMode.FULL and not changed_after) or not a.manually_modified:
                m.assignments.remove(a)
    db.flush()

    saved = skipped = kept = 0
    referee_ids = {r for (r,) in db.execute(select(Referee.id))}
    for p in run.result["assignments"]:
        match = matches.get(p["match"]["match_id"])
        role = RefereeRole(p["role"])
        if match is None or p["referee_id"] not in referee_ids or role not in match.required_roles:
            skipped += 1
            continue
        if any(a.role == role for a in match.assignments):
            if p["manually_modified"]:
                kept += 1
            else:
                skipped += 1
            continue
        match.assignments.append(
            Assignment(
                referee_id=p["referee_id"],
                role=role,
                manually_modified=False,
                score=p["score"],
                distance_km=p["distance_km"],
                travel_minutes=p["travel_minutes"],
                explanation=p["explanation"],
            )
        )
        saved += 1
    for m in matches.values():
        m.refresh_status()
    run.status = GenerationRunStatus.CONFIRMED
    run.confirmed_at = dt.datetime.now()
    db.commit()
    return {"run_id": run.id, "saved_assignments": saved, "kept_manual": kept, "skipped": skipped, "stats": run.stats}


# --- odczyt ----------------------------------------------------------------------
def to_read(a: Assignment, conflict: str | None = None) -> dict[str, Any]:
    return {
        "id": a.id,
        "match_id": a.match_id,
        "referee_id": a.referee_id,
        "referee_name": a.referee.full_name if a.referee else "",
        "referee_licenses": (a.referee.licenses or []) if a.referee else [],
        "referee_location": a.referee.location_label if a.referee else "",
        "role": a.role,
        "manually_modified": a.manually_modified,
        "score": a.score,
        "distance_km": a.distance_km,
        "travel_minutes": a.travel_minutes,
        "explanation": a.explanation,
        "conflict": conflict,
    }


def list_assignments(
    db: Session, date_from: dt.date | None = None, date_to: dt.date | None = None, match_id: int | None = None
) -> list[Assignment]:
    q = (
        select(Assignment)
        .join(Match)
        .options(selectinload(Assignment.referee))
        .order_by(Match.date, Match.start_time, Assignment.match_id)
    )
    if date_from:
        q = q.where(Match.date >= date_from)
    if date_to:
        q = q.where(Match.date <= date_to)
    if match_id:
        q = q.where(Assignment.match_id == match_id)
    return list(db.scalars(q))


def board(db: Session, date_from: dt.date, date_to: dt.date) -> list[dict[str, Any]]:
    """Widok obsady: mecze z okresu z przypisaniami i bieżącymi konfliktami."""
    result, _ = scoring_service.evaluate_current(db, date_from, date_to)
    conflicts = {(a.slot.match_id, a.slot.role): a.conflict for a in result.assignments}
    matches = db.scalars(
        select(Match)
        .options(selectinload(Match.venue), selectinload(Match.assignments).selectinload(Assignment.referee))
        .where(Match.date >= date_from, Match.date <= date_to)
        .order_by(Match.date, Match.start_time, Match.id)
    )
    return [
        {
            "match_id": m.id,
            "date": m.date,
            "start_time": m.start_time,
            "estimated_end_time": m.estimated_end_time,
            "league": m.league,
            "home_team": m.home_team,
            "away_team": m.away_team,
            "venue_name": m.venue.name,
            "status": m.status.value,
            "required_roles": m.required_roles,
            "assignments": [to_read(a, conflicts.get((m.id, a.role))) for a in m.assignments],
        }
        for m in matches
    ]


# --- ręczne zmiany --------------------------------------------------------------
def _apply_evaluation(db: Session, assignment: Assignment, match: Match) -> str | None:
    """Uzupełnia score / odległość / uzasadnienie; zwraca ostrzeżenie, jeśli łamie ograniczenia."""
    ev = scoring_service.evaluate_referee(db, match, assignment.role, assignment.referee_id)
    if ev is None:
        return None
    if ev.feasible:
        assignment.score = ev.score
        assignment.distance_km = ev.distance_km
        assignment.travel_minutes = ev.travel_minutes
        assignment.explanation = {**ev.explanation(), "manual": True}
        return None
    assignment.score = None
    assignment.distance_km = None
    assignment.travel_minutes = None
    assignment.explanation = {"reasons": [], "manual": True, "rejection": ev.rejection.message}
    return f"Uwaga: {ev.rejection.message}"


def assign_manually(db: Session, match_id: int, referee_id: int, role: RefereeRole) -> tuple[Assignment, str | None]:
    match = db.get(Match, match_id)
    if match is None:
        raise AssignmentError(f"Mecz {match_id} nie istnieje")
    if db.get(Referee, referee_id) is None:
        raise AssignmentError(f"Sędzia {referee_id} nie istnieje")
    if role not in match.required_roles:
        raise AssignmentError(f"Mecz {match_id} nie wymaga roli {role.value}")
    existing = next((a for a in match.assignments if a.role == role), None)
    if existing is not None:
        match.assignments.remove(existing)
        db.flush()
    assignment = Assignment(match_id=match.id, referee_id=referee_id, role=role, manually_modified=True)
    warning = _apply_evaluation(db, assignment, match)
    match.assignments.append(assignment)
    match.refresh_status()
    db.commit()
    db.refresh(assignment)
    return assignment, warning


def change_referee(db: Session, assignment_id: int, referee_id: int) -> tuple[Assignment, str | None]:
    a = db.get(Assignment, assignment_id)
    if a is None:
        raise AssignmentError(f"Przypisanie {assignment_id} nie istnieje")
    return assign_manually(db, a.match_id, referee_id, a.role)


def delete_assignment(db: Session, assignment_id: int) -> None:
    a = db.get(Assignment, assignment_id)
    if a is None:
        raise AssignmentError(f"Przypisanie {assignment_id} nie istnieje")
    match = a.match
    match.assignments.remove(a)
    match.refresh_status()
    db.commit()


