from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base
from app.models.enums import MatchStatus, RefereeRole, roles_for

if TYPE_CHECKING:
    from app.models.assignment import Assignment
    from app.models.venue import Venue


class Match(Base):
    """Mecz do obsadzenia."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Identyfikator z systemu zewnętrznego (np. strony komisji) — klucz do upsertu przy imporcie.
    external_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    start_time: Mapped[dt.time] = mapped_column(Time)
    estimated_end_time: Mapped[dt.time] = mapped_column(Time)
    league: Mapped[str] = mapped_column(String(100), default="")
    home_team: Mapped[str] = mapped_column(String(200))
    away_team: Mapped[str] = mapped_column(String(200))
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id", ondelete="RESTRICT"))
    required_referees: Mapped[int] = mapped_column(Integer, default=1)
    # Nieużywane przez generator — przyjazd przed meczem to globalne ustawienie (system_settings).
    arrival_before_minutes: Mapped[int] = mapped_column(Integer, default=45)
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, native_enum=False, length=32), default=MatchStatus.UNASSIGNED
    )

    venue: Mapped[Venue] = relationship(back_populates="matches")
    assignments: Mapped[list[Assignment]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )

    @property
    def required_roles(self) -> list[RefereeRole]:
        return roles_for(self.required_referees)

    def refresh_status(self) -> None:
        """Przelicza status na podstawie liczby przypisań (nie rusza meczów odwołanych)."""
        if self.status == MatchStatus.CANCELLED:
            return
        filled = {a.role for a in self.assignments}
        required = set(self.required_roles)
        if required and required <= filled:
            self.status = MatchStatus.ASSIGNED
        elif filled & required:
            self.status = MatchStatus.PARTIALLY_ASSIGNED
        else:
            self.status = MatchStatus.UNASSIGNED
