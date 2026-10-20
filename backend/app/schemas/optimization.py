import datetime as dt
from typing import Any

from pydantic import BaseModel

from app.models.enums import GenerationMode, GenerationRunStatus, RefereeRole
from app.schemas.common import Period


class GenerateRequest(Period):
    mode: GenerationMode = GenerationMode.KEEP_MANUAL


class MatchInfo(BaseModel):
    match_id: int
    date: dt.date
    start_time: str
    end_time: str
    league: str
    home_team: str
    away_team: str
    venue_name: str


class ProposedAssignmentRead(BaseModel):
    match: MatchInfo
    role: RefereeRole
    referee_id: int
    referee_name: str
    referee_licenses: list[str] = []
    referee_location: str = ""
    score: float | None
    distance_km: float | None
    travel_minutes: float | None
    manually_modified: bool
    explanation: dict[str, Any]
    conflict: str | None = None


class ReasonCountRead(BaseModel):
    code: str
    label: str
    count: int


class UnassignedRead(BaseModel):
    match: MatchInfo
    role: RefereeRole
    reasons: list[ReasonCountRead]
    rejected_examples: list[dict[str, str]]


class GenerationStatsRead(BaseModel):
    matches_total: int
    matches_assigned: int
    matches_unassigned: int
    slots_total: int
    slots_assigned: int
    active_referees: int
    referees_used: int
    avg_matches_per_referee: float
    avg_distance_km: float
    total_distance_km: float
    conflicts: int


class GenerationPreview(BaseModel):
    run_id: int
    status: GenerationRunStatus
    params: dict[str, Any]
    stats: GenerationStatsRead
    assignments: list[ProposedAssignmentRead]
    unassigned: list[UnassignedRead]


class ConfirmRequest(BaseModel):
    run_id: int


class ConfirmResponse(BaseModel):
    run_id: int
    saved_assignments: int
    kept_manual: int
    skipped: int
    stats: GenerationStatsRead
