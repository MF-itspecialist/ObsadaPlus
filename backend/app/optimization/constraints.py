"""Twarde ograniczenia (HARD CONSTRAINTS).

Każde ograniczenie to osobna klasa. Kolejność w ``DEFAULT_CONSTRAINTS`` ma
znaczenie: ewaluacja kończy się na pierwszym niespełnionym warunku, a jego kod
trafia do statystyki przyczyn braku obsady. Nowe ograniczenia (konflikt
interesów, region) dodaje się jako kolejne klasy.
"""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.optimization.context import CandidateContext
from app.optimization.domain import fmt_time
from app.optimization.licenses import check_license


@dataclass(frozen=True)
class Rejection:
    code: str
    message: str


# Etykiety kodów odrzucenia (używane w podsumowaniu nieobsadzonych meczów).
REJECTION_LABELS: dict[str, str] = {
    "INACTIVE": "sędzia nieaktywny",
    "NO_LICENSE": "brak wymaganej licencji",
    "NOT_AVAILABLE_DAY": "brak dostępnych sędziów (dyspozycyjność w tym dniu)",
    "OUTSIDE_TIME_WINDOW": "mecz poza godzinami dyspozycyjności",
    "TIME_CONFLICT": "konflikty czasowe",
    "DAILY_LIMIT": "przekroczony dzienny limit spotkań",
    "WEEKEND_LIMIT": "przekroczony weekendowy limit spotkań",
    "NO_TRAVEL_TIME": "brak możliwości transportu (za mało czasu na dojazd)",
}


class HardConstraint(ABC):
    code: str

    @abstractmethod
    def check(self, ctx: CandidateContext) -> Rejection | None:
        """Zwraca ``None`` gdy warunek spełniony, w przeciwnym razie powód odrzucenia."""

    def reject(self, message: str) -> Rejection:
        return Rejection(self.code, message)


class ActiveConstraint(HardConstraint):
    code = "INACTIVE"

    def check(self, ctx: CandidateContext) -> Rejection | None:
        return None if ctx.referee.active else self.reject("sędzia jest nieaktywny")


class LicenseConstraint(HardConstraint):
    """Licencja musi uprawniać do poziomu rozgrywek meczu w danej roli (główny / asystent)."""

    code = "NO_LICENSE"

    def check(self, ctx: CandidateContext) -> Rejection | None:
        reason = check_license(ctx.referee.licenses, ctx.slot.league, ctx.slot.role)
        return self.reject(reason) if reason else None


class DayAvailabilityConstraint(HardConstraint):
    code = "NOT_AVAILABLE_DAY"

    def check(self, ctx: CandidateContext) -> Rejection | None:
        a = ctx.availability
        if a is None:
            return self.reject("brak zgłoszonej dyspozycyjności w tym dniu")
        if not a.available:
            return self.reject("niedostępny w tym dniu")
        return None


class TimeWindowConstraint(HardConstraint):
    """Mecz od wymaganego przyjazdu do końca musi mieścić się w oknie dyspozycyjności."""

    code = "OUTSIDE_TIME_WINDOW"

    def check(self, ctx: CandidateContext) -> Rejection | None:
        start, end = ctx.window_start(), ctx.window_end()
        if start is not None and ctx.slot.required_arrival < start:
            return self.reject(
                f"wymagany przyjazd {fmt_time(ctx.slot.required_arrival)} przed początkiem dyspozycyjności {fmt_time(start)}"
            )
        if end is not None and ctx.slot.end > end:
            return self.reject(f"mecz kończy się {fmt_time(ctx.slot.end)}, dyspozycyjność do {fmt_time(end)}")
        return None


def _overlaps(a_start: dt.datetime, a_end: dt.datetime, b_start: dt.datetime, b_end: dt.datetime) -> bool:
    return a_start < b_end and b_start < a_end


class NoOverlapConstraint(HardConstraint):
    """Brak nakładających się meczów (okres: od wymaganego przyjazdu do końca meczu)."""

    code = "TIME_CONFLICT"

    def check(self, ctx: CandidateContext) -> Rejection | None:
        s = ctx.slot
        for b in ctx.state.bookings_on(ctx.referee.id, s.date):
            if b.slot.key == s.key:
                continue
            if b.slot.match_id == s.match_id or _overlaps(
                s.required_arrival, s.end, b.slot.required_arrival, b.slot.end
            ):
                return self.reject(
                    f"koliduje z meczem {b.slot.label} ({fmt_time(b.slot.start)}–{fmt_time(b.slot.end)})"
                )
        return None


class DailyLimitConstraint(HardConstraint):
    code = "DAILY_LIMIT"

    def check(self, ctx: CandidateContext) -> Rejection | None:
        if ctx.day_count + 1 > ctx.referee.max_matches_per_day:
            return self.reject(f"limit {ctx.referee.max_matches_per_day} meczów dziennie osiągnięty")
        return None


class WeekendLimitConstraint(HardConstraint):
    code = "WEEKEND_LIMIT"

    def check(self, ctx: CandidateContext) -> Rejection | None:
        if ctx.weekend_count + 1 > ctx.referee.max_matches_per_weekend:
            return self.reject(f"limit {ctx.referee.max_matches_per_weekend} meczów w weekend osiągnięty")
        return None


class TravelFeasibilityConstraint(HardConstraint):
    """Możliwość dotarcia na mecz i z meczu na kolejny przydzielony mecz.

    poprzedni_koniec + czas_przejazdu + bufor <= wymagany_przyjazd
    (dla pierwszego meczu dnia: początek_dyspozycyjności + przejazd + bufor).
    """

    code = "NO_TRAVEL_TIME"

    def check(self, ctx: CandidateContext) -> Rejection | None:
        s = ctx.slot
        earliest = ctx.earliest_arrival
        if earliest is not None and earliest > s.required_arrival:
            origin = "z poprzedniego meczu" if ctx.previous else "z domu"
            return self.reject(
                f"dojazd {origin} {ctx.inbound.travel_minutes:.0f} min + bufor "
                f"{ctx.settings.transport_safety_buffer_minutes} min → najwcześniej {fmt_time(earliest)}, "
                f"wymagane {fmt_time(s.required_arrival)}"
            )
        if ctx.next is not None and ctx.outbound is not None:
            nxt = ctx.next.slot
            arrive_next = s.end + dt.timedelta(minutes=ctx.outbound.travel_minutes) + ctx.buffer
            if arrive_next > nxt.required_arrival:
                return self.reject(
                    f"nie zdąży na kolejny mecz {nxt.label}: dotrze {fmt_time(arrive_next)}, "
                    f"wymagane {fmt_time(nxt.required_arrival)}"
                )
        return None


DEFAULT_CONSTRAINTS: tuple[HardConstraint, ...] = (
    ActiveConstraint(),
    LicenseConstraint(),
    DayAvailabilityConstraint(),
    TimeWindowConstraint(),
    NoOverlapConstraint(),
    DailyLimitConstraint(),
    WeekendLimitConstraint(),
    TravelFeasibilityConstraint(),
)
