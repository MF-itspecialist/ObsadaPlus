from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession, not_found
from app.models import GenerationRun
from app.schemas.optimization import ConfirmRequest, ConfirmResponse, GenerateRequest, GenerationPreview
from app.services import assignment_service
from app.services.assignment_service import AssignmentError

router = APIRouter(prefix="/api/optimization", tags=["optimization"])


@router.post("/generate", response_model=GenerationPreview)
def generate(req: GenerateRequest, db: DbSession):
    """Generuje propozycję obsady (podgląd). Nic nie zmienia w obsadzie do czasu /confirm."""
    run = assignment_service.generate_preview(db, req)
    return assignment_service.run_to_preview(db, run)


@router.post("/confirm", response_model=ConfirmResponse)
def confirm(req: ConfirmRequest, db: DbSession):
    """Zatwierdza podgląd i zapisuje obsadę w bazie."""
    try:
        return assignment_service.confirm(db, req.run_id)
    except AssignmentError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/runs/{run_id}", response_model=GenerationPreview)
def get_run(run_id: int, db: DbSession):
    run = db.get(GenerationRun, run_id)
    if run is None:
        raise not_found("Generowanie", run_id)
    return assignment_service.run_to_preview(db, run)


@router.get("/runs", response_model=list[dict])
def list_runs(db: DbSession, limit: int = 20):
    """Historia generowań (bez szczegółów)."""
    runs = db.scalars(select(GenerationRun).order_by(GenerationRun.id.desc()).limit(limit))
    return [
        {"run_id": r.id, "created_at": r.created_at, "status": r.status, "params": r.params, "stats": r.stats}
        for r in runs
    ]
