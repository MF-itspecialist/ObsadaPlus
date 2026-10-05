from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.settings import SystemSettings
from app.services import settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SystemSettings)
def get_settings(db: DbSession):
    return settings_service.get_settings(db)


@router.put("", response_model=SystemSettings)
def update_settings(data: SystemSettings, db: DbSession):
    return settings_service.update_settings(db, data)
