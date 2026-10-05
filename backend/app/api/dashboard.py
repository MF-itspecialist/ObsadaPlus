from fastapi import APIRouter

from app.api.deps import DbSession, PeriodParams
from app.schemas.dashboard import DashboardStats
from app.services import statistics_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardStats)
def dashboard(db: DbSession, p: PeriodParams):
    return statistics_service.dashboard(db, *p)
