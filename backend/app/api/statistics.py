from typing import Any

from fastapi import APIRouter, Response

from app.api.deps import DbSession, PeriodParams
from app.services import export_service, mileage_service

router = APIRouter(prefix="/api/statistics", tags=["statistics"])


@router.get("")
def statistics(db: DbSession, p: PeriodParams) -> dict[str, Any]:
    """Podsumowanie okresu (miesiąc, sezon): mecze, obsada, ligi, kilometry i kwoty na sędziego."""
    return mileage_service.compute(db, *p)


@router.get("/mileage.xlsx")
def mileage_xlsx(db: DbSession, p: PeriodParams):
    """Kilometrówka w Excelu: suma na sędziego, każdy przejazd i podsumowanie miesięcy."""
    content = mileage_service.to_xlsx(mileage_service.compute(db, *p))
    name = export_service.filename("kilometrowka", *p, "xlsx")
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
