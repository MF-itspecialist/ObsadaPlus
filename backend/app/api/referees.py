from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import DbSession, PeriodParams, not_found
from app.models import Referee
from app.schemas.referee import RefereeCreate, RefereeOverview, RefereeRead, RefereeUpdate
from app.services import statistics_service

router = APIRouter(prefix="/api/referees", tags=["referees"])


@router.get("", response_model=list[RefereeRead])
def list_referees(db: DbSession, active: bool | None = None) -> list[Referee]:
    q = select(Referee).order_by(Referee.last_name, Referee.first_name)
    if active is not None:
        q = q.where(Referee.active.is_(active))
    return list(db.scalars(q))


@router.get("/overview", response_model=list[RefereeOverview])
def referees_overview(db: DbSession, p: PeriodParams):
    """Sędziowie z dostępnością i liczbą meczów w poszczególnych dniach okresu."""
    return statistics_service.referee_overview(db, *p)


@router.get("/{referee_id}", response_model=RefereeRead)
def get_referee(referee_id: int, db: DbSession) -> Referee:
    ref = db.get(Referee, referee_id)
    if ref is None:
        raise not_found("Sędzia", referee_id)
    return ref


@router.post("", response_model=RefereeRead, status_code=status.HTTP_201_CREATED)
def create_referee(data: RefereeCreate, db: DbSession) -> Referee:
    ref = Referee(**data.model_dump())
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


@router.put("/{referee_id}", response_model=RefereeRead)
def update_referee(referee_id: int, data: RefereeUpdate, db: DbSession) -> Referee:
    ref = db.get(Referee, referee_id)
    if ref is None:
        raise not_found("Sędzia", referee_id)
    for key, value in data.model_dump().items():
        setattr(ref, key, value)
    db.commit()
    db.refresh(ref)
    return ref


@router.delete("/{referee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_referee(referee_id: int, db: DbSession) -> None:
    ref = db.get(Referee, referee_id)
    if ref is None:
        raise not_found("Sędzia", referee_id)
    matches = {a.match for a in ref.assignments}
    db.delete(ref)
    db.flush()
    for m in matches:
        db.refresh(m)
        m.refresh_status()
    db.commit()
