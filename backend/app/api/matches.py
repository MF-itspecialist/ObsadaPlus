import datetime as dt
import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, not_found
from app.importers import CSVMatchImporter, JSONMatchImporter, ManualMatchImporter, MatchImportRecord
from app.importers.import_service import import_matches
from app.importers.json_importer import ImportFormatError
from app.importers.lnp_importer import LNPMatchImporter
from app.models import Assignment, Match, MatchStatus, Venue
from app.schemas.match import ImportResult, MatchCreate, MatchRead, MatchUpdate
from app.services.settings_service import get_settings

router = APIRouter(prefix="/api/matches", tags=["matches"])


def _to_read(m: Match) -> dict:
    return {
        **{c: getattr(m, c) for c in MatchRead.model_fields if c not in ("venue", "assignments")},
        "venue": m.venue,
        "assignments": [
            {
                "id": a.id,
                "referee_id": a.referee_id,
                "referee_name": a.referee.full_name,
                "role": a.role,
                "manually_modified": a.manually_modified,
                "score": a.score,
                "distance_km": a.distance_km,
                "travel_minutes": a.travel_minutes,
            }
            for a in m.assignments
        ],
    }


def _load(db: DbSession, match_id: int) -> Match:
    m = db.scalar(
        select(Match)
        .options(selectinload(Match.venue), selectinload(Match.assignments).selectinload(Assignment.referee))
        .where(Match.id == match_id)
    )
    if m is None:
        raise not_found("Mecz", match_id)
    return m


def _check_venue(db: DbSession, venue_id: int) -> None:
    if db.get(Venue, venue_id) is None:
        raise HTTPException(422, f"Obiekt {venue_id} nie istnieje")


@router.get("", response_model=list[MatchRead])
def list_matches(
    db: DbSession,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    status_filter: Annotated[MatchStatus | None, Query(alias="status")] = None,
):
    q = (
        select(Match)
        .options(selectinload(Match.venue), selectinload(Match.assignments).selectinload(Assignment.referee))
        .order_by(Match.date, Match.start_time, Match.id)
    )
    if date_from:
        q = q.where(Match.date >= date_from)
    if date_to:
        q = q.where(Match.date <= date_to)
    if status_filter:
        q = q.where(Match.status == status_filter)
    return [_to_read(m) for m in db.scalars(q)]


@router.get("/{match_id}", response_model=MatchRead)
def get_match(match_id: int, db: DbSession):
    return _to_read(_load(db, match_id))


@router.post("", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
def create_match(data: MatchCreate, db: DbSession):
    _check_venue(db, data.venue_id)
    m = Match(**data.model_dump(), status=MatchStatus.UNASSIGNED)
    db.add(m)
    db.commit()
    return _to_read(_load(db, m.id))


@router.put("/{match_id}", response_model=MatchRead)
def update_match(match_id: int, data: MatchUpdate, db: DbSession):
    _check_venue(db, data.venue_id)
    m = _load(db, match_id)
    payload = data.model_dump(exclude={"status"})
    for key, value in payload.items():
        setattr(m, key, value)
    # Zmniejszenie liczby sędziów usuwa przypisania ról, które przestały być wymagane.
    for a in [a for a in m.assignments if a.role not in m.required_roles]:
        m.assignments.remove(a)
    if data.status == MatchStatus.CANCELLED:
        m.status = MatchStatus.CANCELLED
    else:
        if m.status == MatchStatus.CANCELLED:
            m.status = MatchStatus.UNASSIGNED
        m.refresh_status()
    db.commit()
    return _to_read(_load(db, match_id))


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match(match_id: int, db: DbSession) -> None:
    m = db.get(Match, match_id)
    if m is None:
        raise not_found("Mecz", match_id)
    db.delete(m)
    db.commit()


def _is_lnp_export(content: bytes) -> bool:
    try:
        return LNPMatchImporter.is_lnp_export(json.loads(content))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False


@router.post("/import", response_model=ImportResult)
async def import_file(db: DbSession, file: UploadFile = File(...)):
    """Import meczów z pliku .json lub .csv (upsert po external_id).

    Plik JSON z eksportu terminarza Łączy Nas Piłka (``tools/lnp-export.js``) jest rozpoznawany
    automatycznie; z niego importowane są tylko mecze od dziś.
    """
    content = await file.read()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix == ".csv":
        importer = CSVMatchImporter(content)
    elif _is_lnp_export(content):
        importer = LNPMatchImporter(content)
    else:
        importer = JSONMatchImporter(content)
    try:
        return import_matches(db, importer, get_settings(db).default_match_duration_minutes)
    except ImportFormatError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/import/json", response_model=ImportResult)
def import_json(records: list[MatchImportRecord], db: DbSession):
    """Import meczów przesłanych w treści żądania (lista rekordów)."""
    return import_matches(db, ManualMatchImporter(records), get_settings(db).default_match_duration_minutes)
