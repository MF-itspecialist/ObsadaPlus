"""Wspólne zależności FastAPI. Tu w przyszłości trafi uwierzytelnianie i role użytkowników."""

import datetime as dt
from typing import Annotated

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.db import get_db

DbSession = Annotated[Session, Depends(get_db)]


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
