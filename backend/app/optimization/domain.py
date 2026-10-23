"""Obiekty domenowe silnika obsady (czyste dataclassy, bez ORM)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from app.models.enums import RefereeRole
from app.services.routing_service import GeoPoint


def round_saturday(day: dt.date) -> dt.date:
    """Sobota "kolejki", do której należy dzień.

    Kolejka obejmuje dni od wtorku do poniedziałku, a dni obsadowe to piątek–poniedziałek:
    wtorek–sobota należą do najbliższej soboty, niedziela i poniedziałek do poprzedniej.
    """
    wd = day.weekday()  # pon = 0 … nd = 6
    if wd == 6:
        return day - dt.timedelta(days=1)
    if wd == 0:
        return day - dt.timedelta(days=2)
    return day + dt.timedelta(days=5 - wd)


def round_bounds(day: dt.date) -> tuple[dt.date, dt.date]:
    """Pełny zakres kolejki (wtorek–poniedziałek) zawierającej dzień."""
    sat = round_saturday(day)
    return sat - dt.timedelta(days=4), sat + dt.timedelta(days=2)


def weekend_key(day: dt.date) -> dt.date:
    """Klucz limitu weekendowego: piątek, sobota, niedziela i poniedziałek mają ten sam klucz."""
    return round_saturday(day)


def fmt_time(value: dt.time | dt.datetime | None) -> str:
    return value.strftime("%H:%M") if value else "—"


@dataclass(frozen=True)
class OptimizationSettings:
    """Parametry generatora (domyślne wartości = specyfikacja MVP)."""

    transport_safety_buffer_minutes: int = 15
    distance_weight: float = 2.0
    travel_time_weight: float = 0.5
    daily_match_weight: float = 20.0
    weekend_match_weight: float = 10.0
    workload_balance_weight: float = 10.0
    # Progi kary za odległość: (górna granica km, kara). Ostatni próg obejmuje resztę.
    distance_brackets: tuple[tuple[float, float], ...] = (
        (10, 0),
        (20, 10),
        (30, 30),
        (50, 70),
        (75, 150),
        (float("inf"), 300),
    )
    # Mnożniki wagi: kolejny mecz w granicach "preferred" vs powyżej "preferred".
    within_preferred_factor: float = 0.25
    over_preferred_factor: float = 1.5
    # Brak wpisu dyspozycyjności = niedostępny (False) czy dostępny cały dzień (True).
    assume_available_without_entry: bool = False
    # Na ile minut przed meczem sędzia ma być na miejscu (jeden bufor dla wszystkich meczów).
    arrival_before_minutes: int = 45
    # Kara za mecz męski dla sędzi z licencją kobiecą — tylko gdy w okresie są mecze kobiet.
    women_priority_penalty: float = 30.0
    # Zespół kilkuosobowy: waga km wspólnego dojazdu (kierowca zabiera pozostałych po drodze).
    crew_route_weight: float = 1.0
    women_matches_in_period: bool = False


@dataclass(frozen=True)
class AvailabilityEntry:
    date: dt.date
    available: bool
    available_from: dt.time | None = None
    available_to: dt.time | None = None

    def describe(self) -> str:
        if not self.available:
            return "niedostępny"
        if self.available_from is None and self.available_to is None:
            return "dostępny cały dzień"
        start = fmt_time(self.available_from) if self.available_from else "00:00"
        end = fmt_time(self.available_to) if self.available_to else "24:00"
        return f"dostępny {start}–{end}"


@dataclass
class RefereeProfile:
    id: int
    name: str
    home: GeoPoint
    active: bool = True
    preferred_matches_per_day: int = 2
    max_matches_per_day: int = 3
    preferred_matches_per_weekend: int = 4
    max_matches_per_weekend: int = 5
    availability: dict[dt.date, AvailabilityEntry] = field(default_factory=dict)
    # Przydzielone licencje (nazwy z app.optimization.licenses.LICENSE_RULES).
    licenses: tuple[str, ...] = ()
    # Rozbudowa: preferred_leagues, avoided_clubs, region…


@dataclass(frozen=True)
class Slot:
    """Jedno miejsce do obsadzenia: mecz × rola."""

    match_id: int
    role: RefereeRole
    date: dt.date
    start: dt.datetime
    end: dt.datetime
    arrival_before_minutes: int
    venue: GeoPoint
    label: str = ""
    league: str = ""

    @property
    def key(self) -> tuple[int, RefereeRole]:
        return (self.match_id, self.role)

    @property
    def required_arrival(self) -> dt.datetime:
        """Najpóźniejsza godzina przyjazdu na obiekt."""
        return self.start - dt.timedelta(minutes=self.arrival_before_minutes)


@dataclass(frozen=True)
class FixedBooking:
    """Przypisanie, którego generator nie zmienia (ręczne lub spoza okresu generowania)."""

    slot: Slot
    referee_id: int
    manually_modified: bool = True
    # True → slot należy do generowanego okresu i ma się pojawić w wyniku.
    in_scope: bool = True


@dataclass
class Problem:
    """Pełne dane wejściowe generatora."""

    slots: list[Slot]
    referees: list[RefereeProfile]
    fixed: list[FixedBooking] = field(default_factory=list)
    settings: OptimizationSettings = field(default_factory=OptimizationSettings)

    def referee(self, referee_id: int) -> RefereeProfile | None:
        return next((r for r in self.referees if r.id == referee_id), None)
