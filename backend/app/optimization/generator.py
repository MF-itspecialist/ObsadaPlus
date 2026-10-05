"""Generator obsady: ``AssignmentGenerator.generate_assignments(problem)``.

``AssignmentStrategy`` to punkt podłączenia innych algorytmów. MVP używa
``GreedyScoringStrategy``: mecze chronologicznie, dla każdego najlepszy
(najniższy SCORE) sędzia spełniający twarde ograniczenia. Strategia OR-Tools /
CP-SAT dostanie ten sam ``Problem`` i zwróci ten sam ``GenerationResult``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from app.models.enums import ROLE_ORDER
from app.optimization.constraints import REJECTION_LABELS
from app.optimization.evaluator import CandidateEvaluation, CandidateEvaluator
from app.optimization.domain import Problem, Slot
from app.optimization.state import Booking, ScheduleState, state_without
from app.services.routing_service import RoutingService


@dataclass
class ProposedAssignment:
    slot: Slot
    referee_id: int
    referee_name: str
    score: float | None
    distance_km: float | None
    travel_minutes: float | None
    manually_modified: bool
    explanation: dict[str, Any]
    conflict: str | None = None


@dataclass
class ReasonCount:
    code: str
    label: str
    count: int


@dataclass
class UnassignedSlot:
    slot: Slot
    reasons: list[ReasonCount]
    # Najbliżsi odrzuceni kandydaci (do podpowiedzi w UI).
    rejected_examples: list[dict[str, str]] = field(default_factory=list)


@dataclass
class GenerationStats:
    matches_total: int = 0
    matches_assigned: int = 0
    matches_unassigned: int = 0
    slots_total: int = 0
    slots_assigned: int = 0
    active_referees: int = 0
    referees_used: int = 0
    avg_matches_per_referee: float = 0.0
    avg_distance_km: float = 0.0
    total_distance_km: float = 0.0
    conflicts: int = 0


@dataclass
class GenerationResult:
    assignments: list[ProposedAssignment]
    unassigned: list[UnassignedSlot]
    stats: GenerationStats


def slot_sort_key(slot: Slot) -> tuple:
    return (slot.start, slot.match_id, ROLE_ORDER.index(slot.role) if slot.role in ROLE_ORDER else 99)


class AssignmentStrategy(ABC):
    @abstractmethod
    def solve(self, problem: Problem, evaluator: CandidateEvaluator) -> GenerationResult: ...


class GreedyScoringStrategy(AssignmentStrategy):
    """Zachłanny przydział chronologiczny z oceną punktową."""

    def solve(self, problem: Problem, evaluator: CandidateEvaluator) -> GenerationResult:
        state = ScheduleState()
        for fb in problem.fixed:
            state.add(Booking(slot=fb.slot, referee_id=fb.referee_id, fixed=True))

        active = [r for r in problem.referees if r.active]
        fixed_keys = {fb.slot.key for fb in problem.fixed}
        proposed: dict[tuple, ProposedAssignment] = {}
        unassigned: list[UnassignedSlot] = []

        for slot in sorted(problem.slots, key=slot_sort_key):
            if slot.key in fixed_keys:
                continue
            average_load = len(state.all_bookings()) / len(active) if active else 0.0
            evaluations = evaluator.evaluate_all(problem.referees, slot, state, average_load)
            best = next((e for e in evaluations if e.feasible), None)
            if best is None:
                unassigned.append(self._unassigned(slot, evaluations))
                continue
            state.add(Booking(slot=slot, referee_id=best.referee_id))
            proposed[slot.key] = self._proposal(slot, best, manual=False)

        # Przypisania zablokowane (ręczne) z okresu generowania — ocena na stanie końcowym.
        for fb in problem.fixed:
            if not fb.in_scope:
                continue
            ref = problem.referee(fb.referee_id)
            if ref is None:
                continue
            ev = evaluator.evaluate(ref, fb.slot, state_without(state, fb.slot.key))
            proposed[fb.slot.key] = self._proposal(fb.slot, ev, manual=fb.manually_modified)

        assignments = sorted(proposed.values(), key=lambda p: slot_sort_key(p.slot))
        stats = compute_stats(problem, assignments, unassigned)
        return GenerationResult(assignments=assignments, unassigned=unassigned, stats=stats)

    @staticmethod
    def _proposal(slot: Slot, ev: CandidateEvaluation, manual: bool) -> ProposedAssignment:
        return ProposedAssignment(
            slot=slot,
            referee_id=ev.referee_id,
            referee_name=ev.referee_name,
            score=ev.score,
            distance_km=ev.distance_km,
            travel_minutes=ev.travel_minutes,
            manually_modified=manual,
            explanation=ev.explanation(),
            conflict=ev.rejection.message if ev.rejection else None,
        )

    @staticmethod
    def _unassigned(slot: Slot, evaluations: list[CandidateEvaluation]) -> UnassignedSlot:
        counts = Counter(e.rejection.code for e in evaluations if e.rejection)
        reasons = [
            ReasonCount(code=code, label=REJECTION_LABELS.get(code, code), count=n)
            for code, n in counts.most_common()
            if code != "INACTIVE"
        ]
        examples = [
            {"referee": e.referee_name, "reason": e.rejection.message}
            for e in evaluations
            if e.rejection and e.rejection.code != "INACTIVE"
        ][:5]
        return UnassignedSlot(slot=slot, reasons=reasons, rejected_examples=examples)


def compute_stats(
    problem: Problem, assignments: list[ProposedAssignment], unassigned: list[UnassignedSlot]
) -> GenerationStats:
    match_ids = {s.match_id for s in problem.slots}
    unassigned_matches = {u.slot.match_id for u in unassigned}
    active = sum(1 for r in problem.referees if r.active)
    distances = [a.distance_km for a in assignments if a.distance_km is not None]
    total_km = round(sum(distances), 1)
    return GenerationStats(
        matches_total=len(match_ids),
        matches_assigned=len(match_ids - unassigned_matches),
        matches_unassigned=len(unassigned_matches),
        slots_total=len(problem.slots),
        slots_assigned=len(assignments),
        active_referees=active,
        referees_used=len({a.referee_id for a in assignments}),
        avg_matches_per_referee=round(len(assignments) / active, 2) if active else 0.0,
        avg_distance_km=round(total_km / len(distances), 1) if distances else 0.0,
        total_distance_km=total_km,
        conflicts=sum(1 for a in assignments if a.conflict),
    )


class AssignmentGenerator:
    """Fasada generatora: routing + ustawienia + wymienna strategia."""

    def __init__(self, routing: RoutingService, strategy: AssignmentStrategy | None = None) -> None:
        self.routing = routing
        self.strategy = strategy or GreedyScoringStrategy()

    def generate_assignments(self, problem: Problem) -> GenerationResult:
        evaluator = CandidateEvaluator(self.routing, problem.settings)
        return self.strategy.solve(problem, evaluator)

    def rank_candidates(
        self, problem: Problem, slot: Slot, bookings: list[Booking]
    ) -> list[CandidateEvaluation]:
        """Ranking sędziów dla jednego slotu przy istniejących przypisaniach (ręczna zmiana)."""
        state = ScheduleState()
        for b in bookings:
            if b.slot.key != slot.key:
                state.add(b)
        active = [r for r in problem.referees if r.active]
        average_load = len(state.all_bookings()) / len(active) if active else 0.0
        evaluator = CandidateEvaluator(self.routing, problem.settings)
        return evaluator.evaluate_all(problem.referees, slot, state, average_load)
