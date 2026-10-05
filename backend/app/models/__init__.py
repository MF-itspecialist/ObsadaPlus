"""Modele ORM. Import tego pakietu rejestruje wszystkie tabele w Base.metadata."""

from app.models.assignment import Assignment
from app.models.availability import Availability
from app.models.enums import GenerationMode, GenerationRunStatus, MatchStatus, RefereeRole
from app.models.generation_run import GenerationRun
from app.models.match import Match
from app.models.referee import Referee
from app.models.system_setting import SystemSetting
from app.models.venue import Venue

__all__ = [
    "Assignment",
    "Availability",
    "GenerationMode",
    "GenerationRun",
    "GenerationRunStatus",
    "Match",
    "MatchStatus",
    "Referee",
    "RefereeRole",
    "SystemSetting",
    "Venue",
]
