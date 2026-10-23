"""Wspólne zależności FastAPI: sesja bazy, okres, zalogowany użytkownik i jego rola."""

import datetime as dt
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.db import get_db

from app.models import User, UserRole
from app.services import auth_service

DbSession = Annotated[Session, Depends(get_db)]
SessionToken = Annotated[str | None, Cookie(alias=auth_service.SESSION_COOKIE)]


def current_user(db: DbSession, token: SessionToken = None) -> User:
    user = auth_service.user_for_token(db, token)
    if user is None:
        raise HTTPException(401, "Zaloguj się")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(403, "Ta część jest dostępna tylko dla obsadzającego")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def period(
    date_from: Annotated[dt.date, Query(description="Początek okresu (włącznie)")],
    date_to: Annotated[dt.date, Query(description="Koniec okresu (włącznie)")],
) -> tuple[dt.date, dt.date]:
    if date_to < date_from:
        raise HTTPException(422, "date_to nie może być wcześniejsze niż date_from")
    return date_from, date_to


PeriodParams = Annotated[tuple[dt.date, dt.date], Depends(period)]


def not_found(entity: str, id_: int) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{entity} {id_} nie istnieje")
