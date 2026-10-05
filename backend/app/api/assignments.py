import datetime as dt

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, PeriodParams, not_found
from app.models import Match, RefereeRole
from app.schemas.assignment import (
    AssignmentBoardItem,
    AssignmentCreate,
    AssignmentRead,
    AssignmentUpdate,
    CandidateRead,
    ManualAssignmentResult,
)
from app.services import assignment_service, scoring_service
from app.services.assignment_service import AssignmentError

router = APIRouter(prefix="/api/assignments", tags=["assignments"])


@router.get("", response_model=list[AssignmentRead])
def list_assignments(
    db: DbSession,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    match_id: int | None = None,
):
    return [assignment_service.to_read(a) for a in assignment_service.list_assignments(db, date_from, date_to, match_id)]


@router.get("/board", response_model=list[AssignmentBoardItem])
def assignment_board(db: DbSession, p: PeriodParams):
    """Widok obsady: mecze okresu z przypisaniami i bieżącymi konfliktami."""
    return assignment_service.board(db, *p)


@router.get("/candidates", response_model=list[CandidateRead])
def candidates(match_id: int, db: DbSession, role: RefereeRole = RefereeRole.MAIN):
    """Ranking sędziów dla meczu (do ręcznej zmiany obsady)."""
    match = db.get(Match, match_id)
    if match is None:
        raise not_found("Mecz", match_id)
    return [
        {
            "referee_id": c.referee_id,
            "referee_name": c.referee_name,
            "feasible": c.feasible,
            "score": c.score,
            "distance_km": c.distance_km,
            "travel_minutes": c.travel_minutes,
            "reasons": c.reasons,
            "rejection": c.rejection.message if c.rejection else None,
            "score_breakdown": c.breakdown,
        }
        for c in scoring_service.rank_candidates(db, match, role)
    ]


def _result(a, warning):
    return {"assignment": assignment_service.to_read(a, warning), "warning": warning}


@router.post("", response_model=ManualAssignmentResult, status_code=status.HTTP_201_CREATED)
def assign(data: AssignmentCreate, db: DbSession):
    """Ręczne przypisanie (zastępuje dotychczasowego sędziego w tej roli)."""
    try:
        a, warning = assignment_service.assign_manually(db, data.match_id, data.referee_id, data.role)
    except AssignmentError as exc:
        raise HTTPException(422, str(exc)) from exc
    return _result(a, warning)


@router.put("/{assignment_id}", response_model=ManualAssignmentResult)
def change(assignment_id: int, data: AssignmentUpdate, db: DbSession):
    try:
        a, warning = assignment_service.change_referee(db, assignment_id, data.referee_id)
    except AssignmentError as exc:
        raise HTTPException(422, str(exc)) from exc
    return _result(a, warning)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(assignment_id: int, db: DbSession) -> None:
    try:
        assignment_service.delete_assignment(db, assignment_id)
    except AssignmentError as exc:
        raise HTTPException(404, str(exc)) from exc
