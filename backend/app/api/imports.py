from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.api.deps import DbSession
from app.models import ImportRun
from app.services import auto_import_service

router = APIRouter(prefix="/api/imports", tags=["imports"])


def _read(run: ImportRun) -> dict[str, Any]:
    utc = lambda d: d.isoformat() + "Z" if d else None  # noqa: E731 — w bazie naiwny UTC
    return {
        "id": run.id,
        "source": run.source,
        "trigger": run.trigger,
        "status": run.status,
        "started_at": utc(run.started_at),
        "finished_at": utc(run.finished_at),
        "created": run.created,
        "updated": run.updated,
        "changes": run.changes or [],
        "messages": run.messages or [],
    }


@router.get("")
def list_runs(db: DbSession, limit: int = 30) -> list[dict[str, Any]]:
    """Historia importów (najnowsze pierwsze), z listą zmienionych obsadzonych meczów."""
    runs = db.scalars(select(ImportRun).order_by(ImportRun.started_at.desc(), ImportRun.id.desc()).limit(min(limit, 100)))
    return [_read(r) for r in runs]


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def run_now(db: DbSession) -> dict[str, int]:
    """Import z 90minut.pl teraz, w tle; postęp widać w historii."""
    factory = sessionmaker(bind=db.get_bind(), autoflush=False, expire_on_commit=False)
    run_id = auto_import_service.start_background(factory)
    if run_id is None:
        raise HTTPException(409, "Import już trwa")
    return {"run_id": run_id}
