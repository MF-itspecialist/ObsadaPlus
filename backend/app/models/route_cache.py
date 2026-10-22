from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class RouteCacheEntry(Base):
    """Zapamiętana trasa z płatnego/zewnętrznego serwisu (Google, OSRM) — liczona raz."""

    __tablename__ = "route_cache"

    provider: Mapped[str] = mapped_column(String(20), primary_key=True)
    origin_lat: Mapped[float] = mapped_column(Float, primary_key=True)
    origin_lon: Mapped[float] = mapped_column(Float, primary_key=True)
    dest_lat: Mapped[float] = mapped_column(Float, primary_key=True)
    dest_lon: Mapped[float] = mapped_column(Float, primary_key=True)
    distance_km: Mapped[float] = mapped_column(Float)
    travel_minutes: Mapped[float] = mapped_column(Float)
    created_at = mapped_column(DateTime, server_default=func.now())
