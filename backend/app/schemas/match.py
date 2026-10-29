import datetime as dt

from pydantic import BaseModel, Field, model_validator

from app.models.enums import MatchStatus, RefereeRole
from app.schemas.common import ORMModel
from app.schemas.venue import VenueRead


class MatchBase(BaseModel):
    external_id: str | None = None
    date: dt.date
    start_time: dt.time
    estimated_end_time: dt.time
    league: str = ""
    home_team: str = Field(min_length=1, max_length=200)
    away_team: str = Field(min_length=1, max_length=200)
    venue_id: int
    required_referees: int = Field(1, ge=1, le=4)
    # Obserwator: None = automatycznie wg lig z Ustawień (przy tworzeniu) / bez zmian (przy edycji).
    observer_required: bool | None = None

    @model_validator(mode="after")
    def _times(self) -> "MatchBase":
        if self.estimated_end_time <= self.start_time:
            raise ValueError("estimated_end_time musi być późniejszy niż start_time")
        return self


class MatchCreate(MatchBase):
    pass


class MatchUpdate(MatchBase):
    status: MatchStatus | None = None


class MatchAssignmentBrief(ORMModel):
    id: int
    referee_id: int
    referee_name: str
    role: RefereeRole
    manually_modified: bool
    score: float | None
    distance_km: float | None
    travel_minutes: float | None


class MatchRead(MatchBase, ORMModel):
    id: int
    observer_manual: bool = False
    status: MatchStatus
    venue: VenueRead
    assignments: list[MatchAssignmentBrief] = []


class ImportResult(BaseModel):
    created: int
    updated: int
    errors: list[str] = []
    # Obsadzone mecze, którym import zmienił termin, godzinę albo obiekt.
    changes: list[dict] = []
