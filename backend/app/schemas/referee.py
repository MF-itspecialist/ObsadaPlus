import datetime as dt

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel


class RefereeBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    city: str = ""
    address: str = ""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    active: bool = True
    preferred_matches_per_day: int = Field(2, ge=0, le=10)
    max_matches_per_day: int = Field(3, ge=0, le=10)
    preferred_matches_per_weekend: int = Field(4, ge=0, le=20)
    max_matches_per_weekend: int = Field(5, ge=0, le=20)
    notes: str | None = None

    @model_validator(mode="after")
    def _limits(self) -> "RefereeBase":
        if self.preferred_matches_per_day > self.max_matches_per_day:
            raise ValueError("preferred_matches_per_day nie może przekraczać max_matches_per_day")
        if self.preferred_matches_per_weekend > self.max_matches_per_weekend:
            raise ValueError("preferred_matches_per_weekend nie może przekraczać max_matches_per_weekend")
        return self


class RefereeCreate(RefereeBase):
    pass


class RefereeUpdate(RefereeBase):
    """PUT — pełna aktualizacja rekordu."""


class RefereeRead(RefereeBase, ORMModel):
    id: int


class DayLoad(BaseModel):
    date: dt.date
    availability: str
    matches: int


class RefereeOverview(BaseModel):
    """Wiersz widoku sędziów: dane + dostępność i liczba meczów w okresie."""

    referee: RefereeRead
    days: list[DayLoad]
    matches_in_period: int
