"""Miękkie kryteria — SCORE kandydata (niższy = lepszy).

Hierarchia ze specyfikacji realizowana jest przez rząd wielkości kar:
odległość (setki punktów) > liczba meczów (dziesiątki) > wyrównanie (jednostki
do kilkudziesięciu). Dzięki temu równomierność rozstrzyga przy podobnej
logistyce, ale nie wygrywa z odległością.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.optimization.clubs import matching_club
from app.optimization.context import CandidateContext
from app.optimization.domain import OptimizationSettings
from app.optimization.licenses import has_women_license, is_women_match, level_name


def distance_bracket_penalty(distance_km: float, settings: OptimizationSettings) -> float:
    """Kara progowa: 0–10 km: 0, 10–20: 10, 20–30: 30, 30–50: 70, 50–75: 150, 75+: 300."""
    for upper, penalty in settings.distance_brackets:
        if distance_km < upper:
            return float(penalty)
    return float(settings.distance_brackets[-1][1])


def load_penalty(
    new_count: int,
    preferred: int,
    weight: float,
    within_factor: float,
    over_factor: float,
) -> float:
    """Kara za liczbę meczów po przydzieleniu kolejnego.

    Pierwszy mecz jest darmowy. Każdy kolejny w granicach ``preferred`` kosztuje
    ``weight × within_factor`` (mała kara), każdy powyżej ``preferred`` —
    ``weight × over_factor`` (duża kara). Limit ``max`` jest twardym ograniczeniem.
    Przykład (preferred=2, waga 20): 2. mecz = 5 pkt, 3. mecz = 5 + 30 = 35 pkt.
    """
    total = 0.0
    for k in range(2, new_count + 1):
        total += weight * (within_factor if k <= preferred else over_factor)
    return total


class ScoreComponent(ABC):
    key: str
    label: str

    @abstractmethod
    def compute(self, ctx: CandidateContext) -> float: ...


class DistancePenalty(ScoreComponent):
    key = "distance_penalty"
    label = "odległość"

    def compute(self, ctx: CandidateContext) -> float:
        km = ctx.inbound.distance_km
        return distance_bracket_penalty(km, ctx.settings) + km * ctx.settings.distance_weight


class TravelTimePenalty(ScoreComponent):
    key = "travel_time_penalty"
    label = "czas transportu"

    def compute(self, ctx: CandidateContext) -> float:
        return ctx.inbound.travel_minutes * ctx.settings.travel_time_weight


class DailyMatchesPenalty(ScoreComponent):
    key = "daily_matches_penalty"
    label = "liczba meczów w dniu"

    def compute(self, ctx: CandidateContext) -> float:
        s = ctx.settings
        return load_penalty(
            ctx.day_count + 1,
            ctx.referee.preferred_matches_per_day,
            s.daily_match_weight,
            s.within_preferred_factor,
            s.over_preferred_factor,
        )


class WeekendMatchesPenalty(ScoreComponent):
    key = "weekend_matches_penalty"
    label = "liczba meczów w weekend"

    def compute(self, ctx: CandidateContext) -> float:
        s = ctx.settings
        return load_penalty(
            ctx.weekend_count + 1,
            ctx.referee.preferred_matches_per_weekend,
            s.weekend_match_weight,
            s.within_preferred_factor,
            s.over_preferred_factor,
        )


class WorkloadBalancePenalty(ScoreComponent):
    """Kara za posiadanie większej liczby meczów niż średnia aktywnych sędziów."""

    key = "workload_balance_penalty"
    label = "wyrównanie obciążenia"

    def compute(self, ctx: CandidateContext) -> float:
        excess = ctx.total_count - ctx.average_load
        return max(0.0, excess) * ctx.settings.workload_balance_weight


class WomenPriorityPenalty(ScoreComponent):
    """Sędzie z licencją kobiecą najpierw na mecze kobiet: kara za mecz męski, gdy są mecze kobiet do obsadzenia."""

    key = "women_priority_penalty"
    label = "priorytet meczów kobiet"

    def compute(self, ctx: CandidateContext) -> float:
        s = ctx.settings
        if s.women_matches_in_period and has_women_license(ctx.referee.licenses) and not is_women_match(ctx.slot.league):
            return s.women_priority_penalty
        return 0.0


class PreferredLeaguePenalty(ScoreComponent):
    """Sędzia podał preferowane ligi, a mecz jest z innej."""

    key = "preferred_league_penalty"
    label = "liga spoza preferencji"

    def compute(self, ctx: CandidateContext) -> float:
        prefs = ctx.referee.preferred_leagues
        if not prefs:
            return 0.0
        level = level_name(ctx.slot.league)
        return 0.0 if level is None or level in prefs else ctx.settings.preferred_league_penalty


class AvoidedClubPenalty(ScoreComponent):
    """Mecz klubu, którego sędzia woli unikać — tylko gdy nie ma lepszego kandydata."""

    key = "avoided_club_penalty"
    label = "unikany klub"

    def compute(self, ctx: CandidateContext) -> float:
        s = ctx.slot
        return ctx.settings.avoided_club_penalty if matching_club(ctx.referee.avoided_clubs, s.home_team, s.away_team) else 0.0


DEFAULT_COMPONENTS: tuple[ScoreComponent, ...] = (
    DistancePenalty(),
    TravelTimePenalty(),
    DailyMatchesPenalty(),
    WeekendMatchesPenalty(),
    WorkloadBalancePenalty(),
    WomenPriorityPenalty(),
    PreferredLeaguePenalty(),
    AvoidedClubPenalty(),
)


def compute_score(
    ctx: CandidateContext, components: tuple[ScoreComponent, ...] = DEFAULT_COMPONENTS
) -> tuple[float, dict[str, float]]:
    breakdown = {c.key: round(c.compute(ctx), 2) for c in components}
    return round(sum(breakdown.values()), 2), breakdown
