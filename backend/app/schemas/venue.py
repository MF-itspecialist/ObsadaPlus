from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class VenueBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    city: str = ""
    address: str = ""


class VenueInput(VenueBase):
    """Współrzędne są opcjonalne — bez nich backend geokoduje adres."""

    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)


class VenueCreate(VenueInput):
    pass


class VenueUpdate(VenueInput):
    pass


class VenueRead(VenueBase, ORMModel):
    id: int
    latitude: float
    longitude: float
