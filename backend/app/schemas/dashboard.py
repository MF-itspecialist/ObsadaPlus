from pydantic import BaseModel

from app.schemas.common import Period


class DashboardStats(Period):
    matches_total: int
    matches_assigned: int
    matches_unassigned: int
    available_referees: int
    active_referees: int
    avg_matches_per_referee: float
    total_distance_km: float
    avg_distance_km: float
    conflicts: int
