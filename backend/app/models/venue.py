from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base
from app.regions import region_for

if TYPE_CHECKING:
    from app.models.match import Match


class Venue(Base):
    """Miejsce rozegrania meczu (stadion / boisko)."""

    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    city: Mapped[str] = mapped_column(String(100), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    postal_code: Mapped[str] = mapped_column(String(10), default="")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)

    matches: Mapped[list[Match]] = relationship(back_populates="venue")

    @property
    def region(self) -> str:
        """Podokręg MZPN — najbliższa siedziba."""
        return region_for(self.latitude, self.longitude)
