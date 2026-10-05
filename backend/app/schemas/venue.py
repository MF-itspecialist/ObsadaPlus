from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class VenueBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    city: str = ""
    address: str = ""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class VenueCreate(VenueBase):
    pass


class VenueUpdate(VenueBase):
    pass


class VenueRead(VenueBase, ORMModel):
    id: int
