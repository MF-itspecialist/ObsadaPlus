import datetime as dt
import re

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel


EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class RefereeBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    city: str = ""
    address: str = ""
    licenses: list[str] = []
    active: bool = True
    preferred_matches_per_day: int = Field(2, ge=0, le=10)
    max_matches_per_day: int = Field(3, ge=0, le=10)
    preferred_matches_per_weekend: int = Field(4, ge=0, le=20)
    max_matches_per_weekend: int = Field(5, ge=0, le=20)
    notes: str | None = None
    preferred_leagues: list[str] = []
    avoided_clubs: list[str] = []
    conflict_clubs: list[str] = []
    own_region_only: bool = False
    email: str = Field("", max_length=200)
    notify_email: bool = True

    @model_validator(mode="after")
    def _limits(self) -> "RefereeBase":
        if self.preferred_matches_per_day > self.max_matches_per_day:
            raise ValueError("preferred_matches_per_day nie może przekraczać max_matches_per_day")
        if self.preferred_matches_per_weekend > self.max_matches_per_weekend:
            raise ValueError("preferred_matches_per_weekend nie może przekraczać max_matches_per_weekend")
        from app.optimization.licenses import level_options

        unknown = set(self.preferred_leagues) - set(level_options())
        if unknown:
            raise ValueError(f"Nieznane poziomy rozgrywek: {', '.join(sorted(unknown))}")
        self.email = self.email.strip()
        if self.email and not EMAIL.fullmatch(self.email):
            raise ValueError("Niepoprawny adres e-mail")
        clean = lambda xs: list(dict.fromkeys(x.strip() for x in xs if x.strip()))  # noqa: E731
        self.avoided_clubs, self.conflict_clubs = clean(self.avoided_clubs), clean(self.conflict_clubs)
        return self


class RefereeInput(RefereeBase):
    """Współrzędne i dzielnica są opcjonalne — bez nich backend geokoduje adres."""

    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    district: str | None = None


class RefereeCreate(RefereeInput):
    pass


class RefereeUpdate(RefereeInput):
    """PUT — pełna aktualizacja rekordu."""


class RefereeRead(RefereeBase, ORMModel):
    id: int
    district: str
    location_label: str
    region: str
    license_class: str
    license_class_rank: int
    latitude: float
    longitude: float


class DayLoad(BaseModel):
    date: dt.date
    availability: str
    matches: int


class RefereeOverview(BaseModel):
    """Wiersz widoku sędziów: dane + dostępność i liczba meczów w okresie."""

    referee: RefereeRead
    days: list[DayLoad]
    matches_in_period: int
