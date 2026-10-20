import datetime as dt
from typing import Any

from pydantic import BaseModel

from app.models.enums import RefereeRole
from app.schemas.common import ORMModel


class AssignmentCreate(BaseModel):
    """Ręczne przypisanie sędziego (zawsze manually_modified = true)."""

    match_id: int
    referee_id: int
    role: RefereeRole = RefereeRole.MAIN


class AssignmentUpdate(BaseModel):
    referee_id: int


class AssignmentRead(ORMModel):
    id: int
    match_id: int
    referee_id: int
    referee_name: str
    referee_licenses: list[str] = []
    referee_location: str = ""
    role: RefereeRole
    manually_modified: bool
    score: float | None
    distance_km: float | None
    travel_minutes: float | None
    explanation: dict[str, Any] | None = None
    # Aktualny konflikt (np. po ręcznej zmianie) — liczony na bieżąco.
    conflict: str | None = None


class ManualAssignmentResult(BaseModel):
    assignment: AssignmentRead
    warning: str | None = None


class CandidateRead(BaseModel):
    referee_id: int
    referee_name: str
    referee_licenses: list[str] = []
    referee_location: str = ""
    feasible: bool
    score: float | None
    distance_km: float | None
    travel_minutes: float | None
    reasons: list[str]
    rejection: str | None
    score_breakdown: dict[str, float]


class AssignmentBoardItem(BaseModel):
    """Pozycja widoku obsady: mecz + obsada ról."""

    match_id: int
    date: dt.date
    start_time: dt.time
    estimated_end_time: dt.time
    league: str
    home_team: str
    away_team: str
    venue_name: str
    status: str
    required_roles: list[RefereeRole]
    assignments: list[AssignmentRead]
