"""Stan harmonogramu sędziów budowany przyrostowo podczas generowania."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass

from app.optimization.domain import Slot, weekend_key


@dataclass
class Booking:
    slot: Slot
    referee_id: int
    fixed: bool = False


class ScheduleState:
    """Harmonogram: kto, kiedy i gdzie ma mecz. Pozwala znaleźć poprzedni/następny mecz dnia."""

    def __init__(self) -> None:
        self._by_ref_day: dict[int, dict[dt.date, list[Booking]]] = defaultdict(lambda: defaultdict(list))
        self._by_slot: dict[tuple, Booking] = {}

    # --- modyfikacje -------------------------------------------------------
    def add(self, booking: Booking) -> None:
        day = self._by_ref_day[booking.referee_id][booking.slot.date]
        day.append(booking)
        day.sort(key=lambda b: b.slot.start)
        self._by_slot[booking.slot.key] = booking

    # --- zapytania ---------------------------------------------------------
    def bookings_on(self, referee_id: int, day: dt.date) -> list[Booking]:
        return list(self._by_ref_day.get(referee_id, {}).get(day, []))

    def bookings_of(self, referee_id: int) -> list[Booking]:
        days = self._by_ref_day.get(referee_id, {})
        return sorted((b for d in days.values() for b in d), key=lambda b: b.slot.start)

    def all_bookings(self) -> list[Booking]:
        return list(self._by_slot.values())

    def booking_for(self, slot_key: tuple) -> Booking | None:
        return self._by_slot.get(slot_key)

    def count_on_day(self, referee_id: int, day: dt.date) -> int:
        return len(self._by_ref_day.get(referee_id, {}).get(day, []))

    def count_in_weekend(self, referee_id: int, day: dt.date) -> int:
        key = weekend_key(day)
        days = self._by_ref_day.get(referee_id, {})
        return sum(len(b) for d, b in days.items() if weekend_key(d) == key)

    def total(self, referee_id: int) -> int:
        return sum(len(b) for b in self._by_ref_day.get(referee_id, {}).values())

    def neighbours(self, referee_id: int, slot: Slot) -> tuple[Booking | None, Booking | None]:
        """Ostatni mecz przed ``slot`` i pierwszy po nim (tego samego dnia)."""
        prev: Booking | None = None
        nxt: Booking | None = None
        for b in self.bookings_on(referee_id, slot.date):
            if b.slot.key == slot.key:
                continue
            if b.slot.start <= slot.start:
                prev = b
            elif nxt is None:
                nxt = b
        return prev, nxt


def state_without(state: ScheduleState, slot_key: tuple) -> ScheduleState:
    """Kopia stanu bez jednego przypisania (do walidacji istniejących przypisań)."""
    copy = ScheduleState()
    for b in state.all_bookings():
        if b.slot.key != slot_key:
            copy.add(b)
    return copy
