import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class OutboxMessage(Base):
    """Powiadomienie e-mail do sędziego (skrzynka nadawcza + historia wysłanych)."""

    __tablename__ = "outbox_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # UTC
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    referee_id: Mapped[int | None] = mapped_column(ForeignKey("referees.id", ondelete="SET NULL"), nullable=True)
    to_email: Mapped[str] = mapped_column(String(200))
    to_name: Mapped[str] = mapped_column(String(200), default="")
    # "publication" | "availability_reminder" | "test"
    kind: Mapped[str] = mapped_column(String(30))
    # Klucz chroniący przed dublami, np. "availability:2026-10-31".
    topic: Mapped[str] = mapped_column(String(60), default="", index=True)
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    # "pending" (czeka na skrzynkę / wysyłkę) | "sent" | "failed"
    status: Mapped[str] = mapped_column(String(10), default="pending")
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str] = mapped_column(String(500), default="")
