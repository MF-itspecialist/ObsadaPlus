from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession, PeriodParams
from app.services import map_service

router = APIRouter(prefix="/api/map", tags=["map"])


@router.get("")
def period_map(db: DbSession, p: PeriodParams) -> dict[str, Any]:
    """Obiekty z meczami okresu (stan obsady) i trasy sędziów dzień po dniu."""
    return map_service.period_map(db, *p)


@router.get("/route")
def route(points: str = Query(..., description="lat,lng;lat,lng;… — kolejne punkty trasy")) -> dict[str, Any]:
    """Kształt drogi przez punkty (OSRM); bez OSRM linia prosta (``exact: false``)."""
    try:
        pts = [tuple(float(x) for x in p.split(",")) for p in points.split(";") if p]
    except ValueError:
        raise HTTPException(422, "Niepoprawne punkty") from None
    if any(len(p) != 2 or not (-90 <= p[0] <= 90 and -180 <= p[1] <= 180) for p in pts):
        raise HTTPException(422, "Niepoprawne punkty")
    return map_service.route_shape(pts)
