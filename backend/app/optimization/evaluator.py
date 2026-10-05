"""Ocena kandydatów: twarde ograniczenia → SCORE → uzasadnienie."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.optimization.constraints import DEFAULT_CONSTRAINTS, HardConstraint, Rejection
from app.optimization.context import CandidateContext
from app.optimization.domain import OptimizationSettings, RefereeProfile, Slot, fmt_time
from app.optimization.scoring import DEFAULT_COMPONENTS, ScoreComponent, compute_score
from app.optimization.state import ScheduleState
from app.services.routing_service import RoutingService


@dataclass
class CandidateEvaluation:
    referee_id: int
    referee_name: str
    feasible: bool
    rejection: Rejection | None = None
    score: float | None = None
    distance_km: float | None = None
    travel_minutes: float | None = None
    breakdown: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    origin: str = ""

    def explanation(self) -> dict[str, Any]:
        return {
            "reasons": self.reasons,
            "score_breakdown": self.breakdown,
            "origin": self.origin,
            "rejection": self.rejection.message if self.rejection else None,
        }


def _matches_word(n: int) -> str:
    if n == 1:
        return "mecz"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "mecze"
    return "meczów"


def build_reasons(ctx: CandidateContext) -> list[str]:
    """Czytelne uzasadnienie wyboru (lista punktów ✓)."""
    reasons: list[str] = []
    if ctx.availability is not None:
        reasons.append(ctx.availability.describe())
    reasons.append("brak konfliktu czasowego")
    origin = (
        f"z poprzedniego meczu ({ctx.previous.slot.label})" if ctx.previous else "z domu"
    )
    reasons.append(f"odległość {ctx.inbound.distance_km:.1f} km {origin}")
    reasons.append(f"czas transportu {ctx.inbound.travel_minutes:.0f} min")
    reasons.append(
        f"aktualnie posiada {ctx.day_count} {_matches_word(ctx.day_count)} tego dnia, "
        f"{ctx.weekend_count} w weekend"
    )
    earliest = ctx.earliest_arrival
    if earliest is not None:
        lead = (ctx.slot.start - earliest).total_seconds() / 60
        reasons.append(
            f"może dotrzeć {lead:.0f} min przed spotkaniem (najpóźniej {fmt_time(ctx.slot.required_arrival)})"
        )
    else:
        reasons.append(f"zdąży na wymagany przyjazd {fmt_time(ctx.slot.required_arrival)}")
    return reasons


class CandidateEvaluator:
    """Ocenia jednego sędziego dla jednego slotu przy bieżącym stanie harmonogramu."""

    def __init__(
        self,
        routing: RoutingService,
        settings: OptimizationSettings,
        constraints: tuple[HardConstraint, ...] = DEFAULT_CONSTRAINTS,
        components: tuple[ScoreComponent, ...] = DEFAULT_COMPONENTS,
    ) -> None:
        self.routing = routing
        self.settings = settings
        self.constraints = constraints
        self.components = components

    def evaluate(
        self,
        referee: RefereeProfile,
        slot: Slot,
        state: ScheduleState,
        average_load: float = 0.0,
    ) -> CandidateEvaluation:
        ctx = CandidateContext(referee, slot, state, self.settings, self.routing, average_load)
        for constraint in self.constraints:
            rejection = constraint.check(ctx)
            if rejection is not None:
                return CandidateEvaluation(
                    referee_id=referee.id,
                    referee_name=referee.name,
                    feasible=False,
                    rejection=rejection,
                )
        score, breakdown = compute_score(ctx, self.components)
        return CandidateEvaluation(
            referee_id=referee.id,
            referee_name=referee.name,
            feasible=True,
            score=score,
            distance_km=ctx.inbound.distance_km,
            travel_minutes=ctx.inbound.travel_minutes,
            breakdown=breakdown,
            reasons=build_reasons(ctx),
            origin="previous_match" if ctx.previous else "home",
        )

    def evaluate_all(
        self,
        referees: list[RefereeProfile],
        slot: Slot,
        state: ScheduleState,
        average_load: float = 0.0,
    ) -> list[CandidateEvaluation]:
        """Wszyscy sędziowie: najpierw możliwi (rosnąco po SCORE), potem odrzuceni."""
        results = [self.evaluate(r, slot, state, average_load) for r in referees]
        return sorted(results, key=lambda e: (not e.feasible, e.score if e.score is not None else 0, e.referee_name))
