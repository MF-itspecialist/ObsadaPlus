from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.api.deps import DbSession
from app.config import get_config
from app.models import OutboxMessage, Referee
from app.schemas.referee import EMAIL
from app.services import notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _factory(db):
    return sessionmaker(bind=db.get_bind(), autoflush=False, expire_on_commit=False)


def _read(m: OutboxMessage) -> dict[str, Any]:
    utc = lambda d: d.isoformat() + "Z" if d else None  # noqa: E731 — w bazie naiwny UTC
    return {
        "id": m.id,
        "created_at": utc(m.created_at),
        "sent_at": utc(m.sent_at),
        "referee_id": m.referee_id,
        "to_email": m.to_email,
        "to_name": m.to_name,
        "kind": m.kind,
        "subject": m.subject,
        "body": m.body,
        "status": m.status,
        "error": m.error,
    }


@router.get("")
def list_messages(db: DbSession, limit: int = 100) -> list[dict[str, Any]]:
    """Skrzynka nadawcza i historia wysłanych (najnowsze pierwsze)."""
    q = (
        select(OutboxMessage)
        .where(OutboxMessage.to_email != "")
        .order_by(OutboxMessage.created_at.desc(), OutboxMessage.id.desc())
        .limit(min(limit, 500))
    )
    return [_read(m) for m in db.scalars(q)]


@router.get("/status")
def status(db: DbSession) -> dict[str, Any]:
    """Czy jest skrzynka do wysyłki, ile czeka i ilu sędziów nie ma adresu."""
    pending = db.scalar(
        select(func.count()).select_from(OutboxMessage).where(OutboxMessage.status.in_(("pending", "failed")), OutboxMessage.to_email != "")
    )
    active = db.scalar(select(func.count()).select_from(Referee).where(Referee.active.is_(True)))
    with_email = db.scalar(select(func.count()).select_from(Referee).where(Referee.active.is_(True), Referee.email != ""))
    cfg = get_config()
    return {
        "smtp_configured": notification_service.smtp_configured(),
        "smtp_from": cfg.smtp_from or cfg.smtp_user,
        "app_url": cfg.app_url,
        "pending": pending,
        "active_referees": active,
        "referees_with_email": with_email,
    }


@router.post("/send-pending")
def send_pending(db: DbSession) -> dict[str, int]:
    """Wysyła oczekujące i nieudane wiadomości (wymaga skrzynki w .env)."""
    if not notification_service.smtp_configured():
        raise HTTPException(409, "Brak skrzynki do wysyłki: uzupełnij SMTP_HOST, SMTP_USER i SMTP_PASSWORD w pliku .env")
    return notification_service.send_pending(_factory(db))


class TestMail(BaseModel):
    to: str = Field(min_length=3, max_length=200)


@router.post("/test")
def send_test(data: TestMail, db: DbSession) -> dict[str, Any]:
    """Wiadomość próbna — sprawdzenie skrzynki."""
    if not EMAIL.fullmatch(data.to.strip()):
        raise HTTPException(422, "Niepoprawny adres e-mail")
    msg = OutboxMessage(to_email=data.to.strip(), to_name="", kind="test", topic="", subject="Obsada+: wiadomość próbna",
                        body="To jest wiadomość próbna z Obsada+. Skrzynka do powiadomień działa.", status="pending", error="")
    db.add(msg)
    db.commit()
    result = notification_service.send_pending(_factory(db), ids=[msg.id])
    db.refresh(msg)
    return _read(msg) | {"result": result}
