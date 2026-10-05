import datetime as dt

from pydantic import BaseModel, ConfigDict, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Period(BaseModel):
    """Zakres dat (włącznie)."""

    date_from: dt.date
    date_to: dt.date

    @model_validator(mode="after")
    def _check_order(self) -> "Period":
        if self.date_to < self.date_from:
            raise ValueError("date_to nie może być wcześniejsze niż date_from")
        return self
