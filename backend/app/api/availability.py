import datetime as dt

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.schemas.availability import AvailabilityBulk, AvailabilityRead, AvailabilityUpsert
from app.services import availability_service
from app.services.availability_service import AvailabilityError

router = APIRouter(prefix="/api/availability", tags=["availability"])


@router.get("", response_model=list[AvailabilityRead])
def list_availability(
    db: DbSession,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    referee_id: int | None = None,
):
    return availability_service.list_availability(db, date_from, date_to, referee_id)


@router.post("", response_model=AvailabilityRead)
def upsert_availability(data: AvailabilityUpsert, db: DbSession):
    """Tworzy lub nadpisuje dyspozycyjność sędziego w danym dniu."""
    try:
        return availability_service.upsert(db, data)
    except AvailabilityError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/bulk", response_model=list[AvailabilityRead])
def upsert_bulk(data: AvailabilityBulk, db: DbSession):
    try:
        return availability_service.upsert_many(db, data.items)
    except AvailabilityError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
