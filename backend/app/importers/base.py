"""Interfejs importera meczów i wspólny format rekordu."""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, model_validator


class MatchImportRecord(BaseModel):
    """Mecz w formacie niezależnym od źródła.

    Miejsce można wskazać przez ``venue_id`` albo ``venue_name`` (opcjonalnie z
    adresem i współrzędnymi — wtedy brakujący obiekt zostanie utworzony).
    """

    external_id: str | None = None
    date: dt.date
    start_time: dt.time
    estimated_end_time: dt.time | None = None
    league: str = ""
    home_team: str = Field(min_length=1)
    away_team: str = Field(min_length=1)
    venue_id: int | None = None
    venue_name: str | None = None
    venue_city: str | None = None
    venue_address: str | None = None
    venue_latitude: float | None = None
    venue_longitude: float | None = None
    required_referees: int = Field(1, ge=1, le=4)
    arrival_before_minutes: int = Field(45, ge=0, le=240)

    @model_validator(mode="after")
    def _venue(self) -> "MatchImportRecord":
        if self.venue_id is None and not self.venue_name:
            raise ValueError("wymagane venue_id albo venue_name")
        return self


class MatchImporter(ABC):
    """Źródło meczów. Implementacje: ręczne, JSON, CSV, eksport terminarza Łączy Nas Piłka."""

    source_name: str = "abstract"

    @abstractmethod
    def fetch_matches(self) -> list[MatchImportRecord]:
        """Zwraca listę meczów do zapisania (upsert po ``external_id``)."""

