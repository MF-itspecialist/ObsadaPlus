"""Kontekst oceny pary (sędzia, slot): leniwie liczone dane logistyczne."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from functools import cached_property

from app.optimization.domain import AvailabilityEntry, OptimizationSettings, RefereeProfile, Slot
from app.optimization.state import Booking, ScheduleState
from app.services.routing_service import GeoPoint, RoutingService


@dataclass(frozen=True)
class Leg:
    """Odcinek przejazdu."""

    origin: GeoPoint
    destination: GeoPoint
    distance_km: float
    travel_minutes: float
    from_home: bool


class CandidateContext:
    """Wszystko, czego potrzebują ograniczenia i składniki SCORE dla jednej pary."""

    def __init__(
        self,
        referee: RefereeProfile,
        slot: Slot,
        state: ScheduleState,
        settings: OptimizationSettings,
        routing: RoutingService,
        average_load: float = 0.0,
    ) -> None:
        self.referee = referee
        self.slot = slot
        self.state = state
        self.settings = settings
        self.routing = routing
        self.average_load = average_load

    # --- dyspozycyjność ----------------------------------------------------
    @cached_property
    def availability(self) -> AvailabilityEntry | None:
        entry = self.referee.availability.get(self.slot.date)
        if entry is None and self.settings.assume_available_without_entry:
            return AvailabilityEntry(date=self.slot.date, available=True)
        return entry

    def window_start(self) -> dt.datetime | None:
        a = self.availability
        if a is None or a.available_from is None:
            return None
        return dt.datetime.combine(self.slot.date, a.available_from)

    def window_end(self) -> dt.datetime | None:
        a = self.availability
        if a is None or a.available_to is None:
            return None
        return dt.datetime.combine(self.slot.date, a.available_to)

    # --- harmonogram -------------------------------------------------------
    @cached_property
    def neighbours(self) -> tuple[Booking | None, Booking | None]:
        return self.state.neighbours(self.referee.id, self.slot)

    @property
    def previous(self) -> Booking | None:
        return self.neighbours[0]

    @property
    def next(self) -> Booking | None:
        return self.neighbours[1]

    @cached_property
    def day_count(self) -> int:
        return self.state.count_on_day(self.referee.id, self.slot.date)

    @cached_property
    def weekend_count(self) -> int:
        return self.state.count_in_weekend(self.referee.id, self.slot.date)

    @cached_property
    def total_count(self) -> int:
        return self.state.total(self.referee.id)

    # --- logistyka ---------------------------------------------------------
    def _leg(self, origin: GeoPoint, destination: GeoPoint, from_home: bool) -> Leg:
        route = self.routing.get_route(origin, destination)
        return Leg(origin, destination, route.distance_km, route.travel_minutes, from_home)

    @cached_property
    def inbound(self) -> Leg:
        """Dojazd na mecz: z poprzedniego meczu tego dnia, a jeśli go nie ma — z domu."""
        if self.previous is not None:
            return self._leg(self.previous.slot.venue, self.slot.venue, from_home=False)
        return self._leg(self.referee.home, self.slot.venue, from_home=True)

    @cached_property
    def outbound(self) -> Leg | None:
        """Przejazd na następny, już przydzielony mecz tego dnia."""
        if self.next is None:
            return None
        return self._leg(self.slot.venue, self.next.slot.venue, from_home=False)

    @property
    def buffer(self) -> dt.timedelta:
        return dt.timedelta(minutes=self.settings.transport_safety_buffer_minutes)

    @cached_property
    def earliest_arrival(self) -> dt.datetime | None:
        """Najwcześniejszy możliwy przyjazd (None = nieograniczony — wyjazd z domu bez okna)."""
        travel = dt.timedelta(minutes=self.inbound.travel_minutes)
        if self.previous is not None:
            return self.previous.slot.end + travel + self.buffer
        start = self.window_start()
        if start is not None:
            return start + travel + self.buffer
        return None
