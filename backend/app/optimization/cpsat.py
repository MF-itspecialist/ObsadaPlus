"""Optymalizacja całego okresu naraz (OR-Tools CP-SAT).

Zachłanny generator wybiera najlepszego sędziego mecz po meczu, więc wcześniejszy wybór
może „zabrać” sędziego, który byłby niezbędny gdzie indziej. CP-SAT rozważa wszystkie mecze
okresu jednocześnie:

1. wynik zachłanny jest punktem startowym (podpowiedź) i zabezpieczeniem,
2. zmienna x[sędzia, slot] dla par spełniających twarde ograniczenia „w izolacji”,
3. ograniczenia: jeden sędzia na slot, jedna rola na mecz, brak kolizji i zdążenie
   z meczu na mecz (parami), limity dzienne i weekendowe,
4. cel: najpierw jak najwięcej obsadzonych miejsc (wyższe ligi ważniejsze), potem
   najmniejszy koszt dojazdów, preferencji i obciążenia (te same wagi co SCORE),
5. wybrane pary są sprawdzane zwykłym ewaluatorem; to, co zostało, dopełnia generator
   zachłanny (on też podaje przyczyny braku obsady),
6. wygrywa lepszy z dwóch wyników — CP-SAT nigdy nie pogarsza obsady.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections import defaultdict
from dataclasses import dataclass, replace

from app.optimization.domain import FixedBooking, Problem, Slot, weekend_key
from app.optimization.evaluator import CandidateEvaluator
from app.optimization.generator import (
    AssignmentStrategy,
    GenerationResult,
    GreedyScoringStrategy,
    league_priority,
    slot_sort_key,
)
from app.optimization.state import Booking, ScheduleState

log = logging.getLogger(__name__)

# Składniki SCORE niezależne od reszty obsady (obciążenie modelujemy osobno).
STATIC_COMPONENTS = (
    "distance_penalty",
    "travel_time_penalty",
    "women_priority_penalty",
    "preferred_league_penalty",
    "avoided_club_penalty",
)
SCALE = 10  # CP-SAT liczy na liczbach całkowitych: koszt × 10
FILL_BONUS = 100_000  # obsadzenie miejsca jest ważniejsze niż każdy koszt dojazdu


def ortools_available() -> bool:
    try:
        import ortools.sat.python.cp_model  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class SolveInfo:
    status: str = ""
    seconds: float = 0.0
    used: str = "greedy"  # który wynik wygrał
    note: str = ""


def result_quality(result: GenerationResult) -> tuple[int, float]:
    """Do porównania wyników: więcej obsadzonych miejsc, potem niższy łączny SCORE."""
    filled = sum(1 for a in result.assignments if not a.conflict)
    cost = sum(a.score or 0.0 for a in result.assignments)
    return (-filled, round(cost, 1))


class CpSatStrategy(AssignmentStrategy):
    def __init__(self, time_limit_s: float = 20.0, workers: int = 8) -> None:
        self.time_limit_s = time_limit_s
        self.workers = workers
        self.greedy = GreedyScoringStrategy()
        self.info = SolveInfo()

    def solve(self, problem: Problem, evaluator: CandidateEvaluator) -> GenerationResult:
        baseline = self.greedy.solve(problem, evaluator)
        self.info = SolveInfo()
        if not ortools_available():
            self.info = SolveInfo(note="OR-Tools nie jest zainstalowane — użyto szybkiej metody")
            return self._annotate(baseline)
        try:
            chosen = self._optimize(problem, evaluator, baseline)
        except Exception:  # noqa: BLE001 — optymalizacja jest dodatkiem, wynik zachłanny zawsze jest
            log.exception("CP-SAT nie powiódł się")
            self.info = SolveInfo(note="optymalizacja całego weekendu nie powiodła się — użyto szybkiej metody")
            return self._annotate(baseline)
        if chosen is None:
            return self._annotate(baseline)

        seeded = replace(problem, fixed=[*problem.fixed, *chosen])
        optimized = self.greedy.solve(seeded, evaluator)
        # Pary z CP-SAT nie są ręczne — w podglądzie mają wyglądać jak zwykły wynik generatora.
        chosen_keys = {fb.slot.key for fb in chosen}
        for a in optimized.assignments:
            if a.slot.key in chosen_keys:
                a.manually_modified = False

        if result_quality(optimized) <= result_quality(baseline):
            self.info.used = "cpsat"
            better_slots = -result_quality(optimized)[0] + result_quality(baseline)[0]
            km_diff = optimized.stats.total_distance_km - baseline.stats.total_distance_km
            parts = []
            if better_slots:
                parts.append(f"obsadzone miejsca +{better_slots}")
            if abs(km_diff) >= 0.1:
                parts.append(f"dojazdy {km_diff:+.0f} km")
            self.info.note = "względem szybkiej metody: " + (", ".join(parts) if parts else "ten sam wynik")
            return self._annotate(optimized)
        self.info.note = "szybka metoda dała lepszy wynik — zostawiono ją"
        return self._annotate(baseline)

    def _annotate(self, result: GenerationResult) -> GenerationResult:
        result.stats.optimizer = self.info.used
        result.stats.optimizer_note = self.info.note
        return result

    # ------------------------------------------------------------------------------
    def _optimize(
        self, problem: Problem, evaluator: CandidateEvaluator, baseline: GenerationResult
    ) -> list[FixedBooking] | None:
        from ortools.sat.python import cp_model

        s = problem.settings
        fixed_keys = {fb.slot.key for fb in problem.fixed}
        slots = [sl for sl in problem.slots if sl.key not in fixed_keys]
        if not slots:
            return None
        refs = [r for r in problem.referees if r.active]
        base_state = ScheduleState()
        for fb in problem.fixed:
            base_state.add(Booking(slot=fb.slot, referee_id=fb.referee_id, fixed=True))

        # 1) pary dopuszczalne i ich koszt „statyczny”
        cost: dict[tuple[int, tuple], int] = {}
        for sl in slots:
            for r in refs:
                ev = evaluator.evaluate(r, sl, base_state)
                if ev.feasible:
                    cost[(r.id, sl.key)] = round(SCALE * sum(ev.breakdown.get(k, 0.0) for k in STATIC_COMPONENTS))
        if not cost:
            return None

        model = cp_model.CpModel()
        terms: list = []  # kary obciążenia i wyrównania (wyrażenia liniowe)
        x = {pair: model.NewBoolVar(f"x_{pair[0]}_{pair[1][0]}_{pair[1][1].value}") for pair in cost}
        by_slot: dict[tuple, list] = defaultdict(list)
        by_ref: dict[int, list[Slot]] = defaultdict(list)
        slot_by_key = {sl.key: sl for sl in slots}
        for (rid, key), var in x.items():
            by_slot[key].append(var)
            by_ref[rid].append(slot_by_key[key])

        for key, vars_ in by_slot.items():
            model.AddAtMostOne(vars_)

        buffer = dt.timedelta(minutes=s.transport_safety_buffer_minutes)
        routing = evaluator.routing
        refs_by_id = {r.id: r for r in refs}

        def compatible(a: Slot, b: Slot) -> bool:
            """Czy sędzia zdąży z meczu a na mecz b (a wcześniej)."""
            if a.match_id == b.match_id:
                return False
            gap = b.required_arrival - a.end
            if gap < buffer:
                return False
            if gap >= dt.timedelta(hours=4):
                return True
            travel = routing.get_travel_time(a.venue, b.venue)
            return a.end + dt.timedelta(minutes=travel) + buffer <= b.required_arrival

        for rid, rslots in by_ref.items():
            ref = refs_by_id[rid]
            per_day: dict[dt.date, list[Slot]] = defaultdict(list)
            per_weekend: dict[dt.date, list[Slot]] = defaultdict(list)
            for sl in rslots:
                per_day[sl.date].append(sl)
                per_weekend[weekend_key(sl.date)].append(sl)
            for day, dslots in per_day.items():
                dslots.sort(key=lambda sl: sl.start)
                for i, a in enumerate(dslots):
                    for b in dslots[i + 1:]:
                        if not compatible(a, b):
                            model.AddBoolOr([x[(rid, a.key)].Not(), x[(rid, b.key)].Not()])
                fixed_n = base_state.count_on_day(rid, day)
                count = sum(x[(rid, sl.key)] for sl in dslots)
                model.Add(count + fixed_n <= ref.max_matches_per_day)
                self._load_penalty(model, count, fixed_n, ref.preferred_matches_per_day, s.daily_match_weight, s, terms)
            for wk, wslots in per_weekend.items():
                fixed_n = base_state.count_in_weekend(rid, wslots[0].date)
                count = sum(x[(rid, sl.key)] for sl in wslots)
                model.Add(count + fixed_n <= ref.max_matches_per_weekend)
                self._load_penalty(model, count, fixed_n, ref.preferred_matches_per_weekend, s.weekend_match_weight, s, terms)

        # wyrównanie: kara za mecze ponad średnią (cel = miejsca / aktywni sędziowie)
        target = -(-(len(slots) + len(problem.fixed)) // max(1, len(refs)))
        for rid, rslots in by_ref.items():
            total = sum(x[(rid, sl.key)] for sl in rslots) + len(base_state.bookings_of(rid))
            over = model.NewIntVar(0, len(rslots) + 10, f"bal_{rid}")
            model.Add(over >= total - target)
            terms.append(round(SCALE * s.workload_balance_weight) * over)

        fill = [(FILL_BONUS + 100 * (60 - league_priority(slot_by_key[key].league))) * var for (rid, key), var in x.items()]
        model.Minimize(sum(c * x[p] for p, c in cost.items()) + sum(terms) - sum(fill))

        # podpowiedź: wynik zachłanny
        greedy_pick = {a.slot.key: a.referee_id for a in baseline.assignments}
        for (rid, key), var in x.items():
            model.AddHint(var, greedy_pick.get(key) == rid)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_s
        solver.parameters.num_search_workers = self.workers
        status = solver.Solve(model)
        self.info.status = solver.StatusName(status)
        self.info.seconds = round(solver.WallTime(), 1)
        log.info("CP-SAT: %s w %.1f s, %d zmiennych", self.info.status, self.info.seconds, len(x))
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            self.info.note = "optymalizacja nie znalazła rozwiązania w limicie czasu — użyto szybkiej metody"
            return None

        picked = sorted(
            ((slot_by_key[key], rid) for (rid, key), var in x.items() if solver.Value(var)),
            key=lambda p: slot_sort_key(p[0]),
        )
        # 2) sprawdzenie zwykłym ewaluatorem (dojazd z poprzedniego meczu, okna dyspozycyjności)
        state = ScheduleState()
        for fb in problem.fixed:
            state.add(Booking(slot=fb.slot, referee_id=fb.referee_id, fixed=True))
        accepted: list[FixedBooking] = []
        for sl, rid in picked:
            if evaluator.evaluate(refs_by_id[rid], sl, state).feasible:
                state.add(Booking(slot=sl, referee_id=rid))
                accepted.append(FixedBooking(slot=sl, referee_id=rid, manually_modified=False, in_scope=True))
        return accepted

    @staticmethod
    def _load_penalty(model, count, fixed_n: int, preferred: int, weight: float, s, terms: list) -> None:
        """Kara za liczbę meczów jak w SCORE: 2.–preferred mecz × within, powyżej × over."""
        if weight <= 0:
            return
        n = count + fixed_n
        extra = model.NewIntVar(0, 50, "extra")  # mecze ponad pierwszy
        model.Add(extra >= n - 1)
        over = model.NewIntVar(0, 50, "over")  # mecze ponad preferowaną liczbę
        model.Add(over >= n - max(1, preferred))
        model.Add(over <= extra)
        within_c = round(SCALE * weight * s.within_preferred_factor)
        over_c = round(SCALE * weight * s.over_preferred_factor)
        terms.append(within_c * (extra - over) + over_c * over)
