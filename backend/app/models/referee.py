from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.availability import Availability


class Referee(Base):
    """Sędzia. Pozycja (latitude/longitude) to punkt startowy pierwszego meczu dnia."""

    __tablename__ = "referees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100), index=True)
    city: Mapped[str] = mapped_column(String(100), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_matches_per_day: Mapped[int] = mapped_column(Integer, default=2)
    max_matches_per_day: Mapped[int] = mapped_column(Integer, default=3)
    preferred_matches_per_weekend: Mapped[int] = mapped_column(Integer, default=4)
    max_matches_per_weekend: Mapped[int] = mapped_column(Integer, default=5)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Miejsca na rozbudowę: level (klasa sędziowska), licencje do lig, region…

    availability: Mapped[list[Availability]] = relationship(
        back_populates="referee", cascade="all, delete-orphan"
    )
    assignments: Mapped[list[Assignment]] = relationship(
        back_populates="referee", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
