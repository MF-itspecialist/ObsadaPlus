import datetime as dt
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base
from app.models.enums import GenerationRunStatus


class GenerationRun(Base):
    """Wynik jednego uruchomienia generatora: podgląd do zatwierdzenia i historia."""

    __tablename__ = "generation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    confirmed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[GenerationRunStatus] = mapped_column(
        Enum(GenerationRunStatus, native_enum=False, length=32), default=GenerationRunStatus.PREVIEW
    )
    params: Mapped[dict[str, Any]] = mapped_column(JSON)
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    stats: Mapped[dict[str, Any]] = mapped_column(JSON)
