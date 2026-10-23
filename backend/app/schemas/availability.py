import datetime as dt

from pydantic import BaseModel, model_validator

from app.schemas.common import ORMModel


class AvailabilityBase(BaseModel):
    referee_id: int
    date: dt.date
    available_from: dt.time | None = None
    available_to: dt.time | None = None
    available: bool = True

    @model_validator(mode="after")
    def _window(self) -> "AvailabilityBase":
        if self.available_from and self.available_to and self.available_to <= self.available_from:
            raise ValueError("available_to musi być późniejsze niż available_from")
        return self


class AvailabilityUpsert(AvailabilityBase):
    """POST /api/availability — tworzy lub nadpisuje wpis (referee_id, date)."""


class AvailabilityRead(AvailabilityBase, ORMModel):
    id: int
    declared_by_referee: bool = False
    declared_at: dt.datetime | None = None


class OwnAvailabilityItem(BaseModel):
    """Dzień zgłaszany przez sędziego w panelu (referee_id bierze się z konta)."""

    date: dt.date
    available_from: dt.time | None = None
    available_to: dt.time | None = None
    available: bool = True

    @model_validator(mode="after")
    def _window(self) -> "OwnAvailabilityItem":
        if self.available_from and self.available_to and self.available_to <= self.available_from:
            raise ValueError("Godzina „do” musi być późniejsza niż „od”")
        return self


class OwnAvailabilitySave(BaseModel):
    items: list[OwnAvailabilityItem] = []
    # Dni, z których sędzia wycofuje zgłoszenie.
    cleared: list[dt.date] = []


class AvailabilityBulk(BaseModel):
    """Zapis dyspozycyjności wielu dni naraz (np. sobota + niedziela z formularza)."""

    items: list[AvailabilityUpsert]
