import datetime as dt
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class Publication(Base):
    """Opublikowana (zamrożona) wersja obsady okresu — to, co dostali sędziowie."""

    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_from: Mapped[dt.date] = mapped_column(Date, index=True)
    date_to: Mapped[dt.date] = mapped_column(Date, index=True)
    version: Mapped[int] = mapped_column(Integer)
    # UTC
    published_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
