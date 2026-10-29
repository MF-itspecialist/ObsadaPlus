import datetime as dt
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, PeriodParams
from app.models import Referee, User, UserRole
from app.schemas.availability import AvailabilityRead, OwnAvailabilitySave
from app.schemas.referee import EMAIL
from app.services import referee_panel_service
from app.services.referee_panel_service import PanelError

router = APIRouter(prefix="/api/me", tags=["referee panel"])


def require_referee(user: CurrentUser) -> User:
    if user.role != UserRole.REFEREE or user.referee_id is None:
        raise HTTPException(403, "Panel sędziego jest dostępny tylko z konta sędziego")
    return user


RefereeUser = Annotated[User, Depends(require_referee)]


@router.get("/matches")
def my_matches(user: RefereeUser, db: DbSession) -> list[dict[str, Any]]:
    """Nadchodzące mecze sędziego z opublikowanej obsady."""
    return referee_panel_service.published_matches(db, user.referee_id)


@router.get("/availability", response_model=list[AvailabilityRead])
def my_availability(user: RefereeUser, db: DbSession, p: PeriodParams):
    return referee_panel_service.own_availability(db, user.referee_id, *p)


@router.put("/availability", response_model=list[AvailabilityRead])
def save_my_availability(data: OwnAvailabilitySave, user: RefereeUser, db: DbSession):
    """Zgłoszenie dyspozycyjności (od jutra, najwyżej 120 dni naprzód)."""
    try:
        return referee_panel_service.save_own_availability(db, user.referee_id, data)
    except PanelError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.get("/today")
def server_today(_: CurrentUser) -> dict[str, dt.date]:
    """Dzisiejsza data wg serwera (Europe/Warsaw) — od niej panel liczy weekendy."""
    return {"today": referee_panel_service.today()}


class Contact(BaseModel):
    email: str = Field("", max_length=200)
    notify_email: bool = True


@router.get("/contact", response_model=Contact)
def my_contact(user: RefereeUser, db: DbSession):
    ref = db.get(Referee, user.referee_id)
    return Contact(email=ref.email, notify_email=ref.notify_email)


@router.put("/contact", response_model=Contact)
def save_my_contact(data: Contact, user: RefereeUser, db: DbSession):
    """Sędzia sam podaje adres do powiadomień o obsadzie i przypomnień."""
    email = data.email.strip()
    if email and not EMAIL.fullmatch(email):
        raise HTTPException(422, "Niepoprawny adres e-mail")
    ref = db.get(Referee, user.referee_id)
    ref.email, ref.notify_email = email, data.notify_email
    db.commit()
    return Contact(email=ref.email, notify_email=ref.notify_email)
