from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base

if TYPE_CHECKING:
    from app.models.referee import Referee


class Availability(Base):
    """Dyspozycyjność sędziego w danym dniu.

    * ``available = False`` → niedostępny cały dzień,
    * ``available = True`` i ``available_from/to = NULL`` → dostępny cały dzień,
    * ``available = True`` i godziny ustawione → dostępny w oknie czasowym.
    """

    __tablename__ = "availability"
    __table_args__ = (UniqueConstraint("referee_id", "date", name="uq_availability_referee_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referee_id: Mapped[int] = mapped_column(ForeignKey("referees.id", ondelete="CASCADE"), index=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    available_from: Mapped[dt.time | None] = mapped_column(Time, nullable=True)
    available_to: Mapped[dt.time | None] = mapped_column(Time, nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True)

    referee: Mapped[Referee] = relationship(back_populates="availability")
