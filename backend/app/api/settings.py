from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.settings import SystemSettings
from app.services import observer_service, settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SystemSettings)
def get_settings(db: DbSession):
    return settings_service.get_settings(db)


@router.put("", response_model=SystemSettings)
def update_settings(data: SystemSettings, db: DbSession):
    saved = settings_service.update_settings(db, data)
    observer_service.apply_levels(db, saved.observer_levels)
    return saved
