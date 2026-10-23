from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base
from app.regions import region_for

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
    # Dzielnica (np. "Mokotów") — uzupełniana automatycznie z adresu przez geokodowanie.
    district: Mapped[str] = mapped_column(String(100), default="")
    # Przydzielone licencje (np. ["Sędzia IV liga", "Asystent III/IV/V liga"]).
    licenses: Mapped[list[str]] = mapped_column(JSON, default=list)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_matches_per_day: Mapped[int] = mapped_column(Integer, default=2)
    max_matches_per_day: Mapped[int] = mapped_column(Integer, default=3)
    preferred_matches_per_weekend: Mapped[int] = mapped_column(Integer, default=4)
    max_matches_per_weekend: Mapped[int] = mapped_column(Integer, default=5)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    availability: Mapped[list[Availability]] = relationship(
        back_populates="referee", cascade="all, delete-orphan"
    )
    assignments: Mapped[list[Assignment]] = relationship(
        back_populates="referee", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def region(self) -> str:
        """Podokręg MZPN (z notatek albo najbliższa siedziba)."""
        return region_for(self.latitude, self.longitude, self.notes)

    @property
    def license_class(self) -> str:
        """Najwyższa klasa rozgrywkowa, którą może prowadzić jako sędzia główny."""
        return self._license_class()[1]

    @property
    def license_class_rank(self) -> int:
        return self._license_class()[0]

    def _license_class(self) -> tuple[int, str]:
        from app.optimization.licenses import license_class  # licencje importują enumy z app.models

        return license_class(self.licenses or [])

    @property
    def location_label(self) -> str:
        """'Warszawa, Mokotów' lub samo miasto, gdy brak dzielnicy."""
        return ", ".join(p for p in (self.city, self.district) if p)
