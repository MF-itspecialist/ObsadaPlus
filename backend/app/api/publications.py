from fastapi import APIRouter, Response, status
from sqlalchemy.orm import sessionmaker

from app.api.deps import DbSession, PeriodParams, not_found
from app.models import Publication
from app.schemas.common import Period
from app.schemas.publication import PublicationRead, PublicationSummary
from app.services import export_service, notification_service, publication_service

router = APIRouter(prefix="/api/publications", tags=["publications"])


@router.post("", response_model=PublicationSummary, status_code=status.HTTP_201_CREATED)
def publish(data: Period, db: DbSession):
    """Publikuje bieżącą obsadę okresu jako kolejną wersję (zamrożona kopia)."""
    previous = publication_service.latest(db, data.date_from, data.date_to)
    pub = publication_service.publish(db, data.date_from, data.date_to)
    notified = notification_service.notify_publication(db, pub, previous)
    notification_service.send_in_background(sessionmaker(bind=db.get_bind(), autoflush=False, expire_on_commit=False))
    return {**publication_service.summary(db, pub), "notifications": notified}


@router.get("/latest", response_model=PublicationSummary | None)
def latest(db: DbSession, p: PeriodParams):
    """Ostatnia publikacja okresu i lista meczów zmienionych od tego czasu (null, gdy nie publikowano)."""
    pub = publication_service.latest(db, *p)
    return publication_service.summary(db, pub) if pub else None


def _get(db, publication_id: int) -> Publication:
    pub = db.get(Publication, publication_id)
    if pub is None:
        raise not_found("Publikacja", publication_id)
    return pub


@router.get("/{publication_id}", response_model=PublicationRead)
def read(publication_id: int, db: DbSession):
    return publication_service.summary(db, _get(db, publication_id), with_rows=True)


@router.get("/{publication_id}/pdf")
def read_pdf(publication_id: int, db: DbSession):
    pub = _get(db, publication_id)
    title = export_service.period_title(pub.date_from, pub.date_to)
    subtitle = f"Wersja {pub.version}, opublikowana {publication_service.local_time(pub).strftime('%d.%m.%Y %H:%M')}"
    pdf = export_service.to_pdf(pub.rows, title, subtitle)
    name = export_service.filename(f"obsada_v{pub.version}", pub.date_from, pub.date_to, "pdf")
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}"'})
