"""Ocena istniejącej obsady i ranking kandydatów (dla ręcznych zmian)."""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.models import Match, RefereeRole
from app.optimization.evaluator import CandidateEvaluation
from app.optimization.generator import AssignmentGenerator, GenerationResult
from app.optimization.state import Booking
from app.services.problem_builder import BuiltProblem, build_problem, make_slot
from app.services.settings_service import get_settings, routing_for, to_optimization_settings


def _generator_and_settings(db: Session):
    s = get_settings(db)
    return AssignmentGenerator(routing_for(s, db)), to_optimization_settings(s)


def evaluate_current(db: Session, date_from: dt.date, date_to: dt.date) -> tuple[GenerationResult, BuiltProblem]:
    """Ocena aktualnie zapisanej obsady: odległości, SCORE i konflikty (bez generowania)."""
    generator, settings = _generator_and_settings(db)
    built = build_problem(db, date_from, date_to, settings, keep_all_existing=True)
    problem = built.problem
    assigned_keys = {fb.slot.key for fb in problem.fixed if fb.in_scope}
    unfilled = [s for s in problem.slots if s.key not in assigned_keys]
    problem.slots = [s for s in problem.slots if s.key in assigned_keys]
    result = generator.generate_assignments(problem)
    # mecze bez obsady liczymy do statystyk jako nieobsadzone
    unfilled_matches = {s.match_id for s in unfilled}
    stats = result.stats
    stats.matches_total = len(built.matches)
    stats.matches_unassigned = len(unfilled_matches)
    stats.matches_assigned = stats.matches_total - stats.matches_unassigned
    stats.slots_total = stats.slots_assigned + len(unfilled)
    return result, built


def rank_candidates(db: Session, match: Match, role: RefereeRole) -> list[CandidateEvaluation]:
    """Ranking wszystkich sędziów dla (mecz, rola) przy pozostałej obsadzie bez zmian."""
    generator, settings = _generator_and_settings(db)
    built = build_problem(db, match.date, match.date, settings, keep_all_existing=True)
    bookings = [Booking(slot=fb.slot, referee_id=fb.referee_id, fixed=True) for fb in built.problem.fixed]
    return generator.rank_candidates(built.problem, make_slot(match, role, settings.arrival_before_minutes), bookings)


def evaluate_referee(db: Session, match: Match, role: RefereeRole, referee_id: int) -> CandidateEvaluation | None:
    return next((c for c in rank_candidates(db, match, role) if c.referee_id == referee_id), None)
