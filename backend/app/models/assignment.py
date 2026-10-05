from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base
from app.models.enums import RefereeRole

if TYPE_CHECKING:
    from app.models.match import Match
    from app.models.referee import Referee


class Assignment(Base):
    """Przypisanie sędziego do meczu w danej roli."""

    __tablename__ = "assignments"
    __table_args__ = (UniqueConstraint("match_id", "role", name="uq_assignments_match_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    referee_id: Mapped[int] = mapped_column(ForeignKey("referees.id", ondelete="CASCADE"), index=True)
    role: Mapped[RefereeRole] = mapped_column(
        Enum(RefereeRole, native_enum=False, length=32), default=RefereeRole.MAIN
    )
    manually_modified: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    travel_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Uzasadnienie wyboru i rozbicie SCORE (lista powodów, składniki kary, punkt startowy).
    explanation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    match: Mapped[Match] = relationship(back_populates="assignments")
    referee: Mapped[Referee] = relationship(back_populates="assignments")
