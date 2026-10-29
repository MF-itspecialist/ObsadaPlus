import datetime as dt
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class ImportRun(Base):
    """Jedno uruchomienie importu meczów (automatyczne albo ręczne) i jego wynik."""

    __tablename__ = "import_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(40))
    # "auto" (harmonogram) albo "manual" (przycisk „Uruchom teraz”)
    trigger: Mapped[str] = mapped_column(String(10))
    # "running" | "ok" | "error"
    status: Mapped[str] = mapped_column(String(10), default="running")
    # UTC
    started_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    # Obsadzone mecze, którym import zmienił termin, godzinę albo obiekt.
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    messages: Mapped[list[str]] = mapped_column(JSON, default=list)
