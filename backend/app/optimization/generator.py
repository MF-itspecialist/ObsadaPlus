"""Generator obsady: ``AssignmentGenerator.generate_assignments(problem)``.

``AssignmentStrategy`` to punkt podłączenia innych algorytmów. MVP używa
``GreedyScoringStrategy``: mecze chronologicznie, dla każdego najlepszy
(najniższy SCORE) sędzia spełniający twarde ograniczenia. Mecz z kilkoma
sędziami (G + A1 + A2) obsadzany jest jako zespół: wybierany jest skład
z najniższym łącznym SCORE, czyli z uwzględnieniem tras wszystkich sędziów. Strategia OR-Tools /
CP-SAT dostanie ten sam ``Problem`` i zwróci ten sam ``GenerationResult``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from itertools import groupby, permutations
from typing import Any

from app.models.enums import ROLE_ORDER
from app.optimization.constraints import REJECTION_LABELS
from app.optimization.evaluator import CandidateEvaluation, CandidateEvaluator
from app.optimization.domain import Problem, RefereeProfile, Slot
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

    def __init__(self, crew_candidates: int = 6) -> None:
        # Ilu najlepszych kandydatów na każdą rolę rozważać przy doborze zespołu.
        self.crew_candidates = crew_candidates

    def solve(self, problem: Problem, evaluator: CandidateEvaluator) -> GenerationResult:
        state = ScheduleState()
        for fb in problem.fixed:
            state.add(Booking(slot=fb.slot, referee_id=fb.referee_id, fixed=True))

        active = [r for r in problem.referees if r.active]
        fixed_keys = {fb.slot.key for fb in problem.fixed}
        proposed: dict[tuple, ProposedAssignment] = {}
        unassigned: list[UnassignedSlot] = []

        open_slots = [s for s in sorted(problem.slots, key=slot_sort_key) if s.key not in fixed_keys]
        for _, group in groupby(open_slots, key=lambda s: (s.start, s.match_id)):
            slots = list(group)
            average_load = len(state.all_bookings()) / len(active) if active else 0.0
            evaluations = {s.key: evaluator.evaluate_all(problem.referees, s, state, average_load) for s in slots}
            ride: SharedRide | None = None
            if len(slots) == 1:
                chosen = {slots[0].key: next((e for e in evaluations[slots[0].key] if e.feasible), None)}
            else:
                crew = choose_crew(
                    slots, evaluations, evaluator.routing,
                    problem.settings.crew_route_weight, self.crew_candidates,
                )
                chosen, ride = crew.members, crew.ride
            for slot in slots:
                best = chosen.get(slot.key)
                if best is None:
                    unassigned.append(self._unassigned(slot, evaluations[slot.key]))
                    continue
                state.add(Booking(slot=slot, referee_id=best.referee_id))
                proposal = self._proposal(slot, best, manual=False)
                if ride is not None:
                    proposal.explanation["reasons"] = [*proposal.explanation["reasons"], ride.describe()]
                    proposal.explanation["shared_ride_km"] = ride.distance_km
                proposed[slot.key] = proposal

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


@dataclass(frozen=True)
class SharedRide:
    """Wspólny dojazd zespołu: kierowca zabiera pozostałych po drodze na obiekt."""

    order: tuple[CandidateEvaluation, ...]  # kierowca, potem kolejno zabierani
    distance_km: float

    def describe(self) -> str:
        names = " → ".join(e.referee_name for e in self.order)
        return f"wspólny dojazd zespołu: {names} → obiekt, {self.distance_km:.1f} km"


def shared_ride(members: list[CandidateEvaluation], venue, routing: RoutingService) -> SharedRide | None:
    """Najkrótsza trasa jednym autem: każdy po kolei jako kierowca, każda kolejność zabierania."""
    if len(members) < 2 or any(m.start_point is None for m in members):
        return None
    best: SharedRide | None = None
    for order in permutations(members):
        points = [m.start_point for m in order] + [venue]
        km = sum(routing.get_distance(a, b) for a, b in zip(points, points[1:]))
        if best is None or km < best.distance_km:
            best = SharedRide(order=tuple(order), distance_km=round(km, 1))
    return best


@dataclass
class CrewChoice:
    members: dict[tuple, CandidateEvaluation | None]
    ride: SharedRide | None
    total_score: float


def choose_crew(
    slots: list[Slot],
    evaluations: dict[tuple, list[CandidateEvaluation]],
    routing: RoutingService,
    route_weight: float,
    limit: int,
) -> CrewChoice:
    """Skład zespołu na jeden mecz (G + A1 + A2 …).

    Kolejność kryteriów: najwięcej obsadzonych ról, potem najniższy koszt zespołu =
    suma SCORE sędziów (każdy z własnym dojazdem i limitami) + ``route_weight`` × km
    wspólnego dojazdu całej trójki. Dzięki temu wygrywają sędziowie, którzy mieszkają
    blisko obiektu i blisko siebie. Jeden sędzia = jedna rola.
    """
    venue = slots[0].venue
    options = [[e for e in evaluations[s.key] if e.feasible][:limit] for s in slots]
    # Trasy między kandydatami (kierowca zabiera kolejnych) — jedną macierzą, nie po jednej.
    starts = list({e.start_point.key(): e.start_point for opts in options for e in opts if e.start_point}.values())
    if len(slots) > 1 and len(starts) > 1:
        routing.prefetch(starts, starts)
    best: tuple[tuple[int, float], CrewChoice] | None = None

    def search(i: int, picked: list[CandidateEvaluation | None], used: set[int]) -> None:
        nonlocal best
        if i == len(slots):
            members = [e for e in picked if e is not None]
            ride = shared_ride(members, venue, routing)
            score = sum(e.score or 0.0 for e in members)
            cost = score + (route_weight * ride.distance_km if ride else 0.0)
            key = (-len(members), round(cost, 6))
            if best is None or key < best[0]:
                choice = CrewChoice({s.key: e for s, e in zip(slots, picked)}, ride, round(score, 1))
                best = (key, choice)
            return
        for ev in options[i]:
            if ev.referee_id in used:
                continue
            picked.append(ev)
            used.add(ev.referee_id)
            search(i + 1, picked, used)
            used.discard(ev.referee_id)
            picked.pop()
        picked.append(None)
        search(i + 1, picked, used)
        picked.pop()

    search(0, [], set())
    assert best is not None
    return best[1]


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

    def prefetch_routes(self, slots: list[Slot], referees: list[RefereeProfile]) -> None:
        """Wszystkie potrzebne trasy jednym zapytaniem na dzień (Google/OSRM liczą macierz).

        Źródła: domy sędziów dostępnych tego dnia + obiekty tego dnia (przejazd między meczami).
        """
        by_day: dict = {}
        for sl in slots:
            by_day.setdefault(sl.date, []).append(sl.venue)
        for day, venues in by_day.items():
            venues = list({v.key(): v for v in venues}.values())
            homes = [
                r.home for r in referees
                if r.active and (r.availability.get(day) is None or r.availability[day].available)
            ]
            self.routing.prefetch([*{h.key(): h for h in homes}.values(), *venues], venues)

    def generate_assignments(self, problem: Problem) -> GenerationResult:
        self.prefetch_routes(problem.slots + [fb.slot for fb in problem.fixed], problem.referees)
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
        self.prefetch_routes([slot, *(b.slot for b in bookings if b.slot.date == slot.date)], problem.referees)
        evaluator = CandidateEvaluator(self.routing, problem.settings)
        return evaluator.evaluate_all(problem.referees, slot, state, average_load)
