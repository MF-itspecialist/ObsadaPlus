import datetime as dt
from typing import Any

from pydantic import BaseModel


class PublicationSummary(BaseModel):
    id: int
    date_from: dt.date
    date_to: dt.date
    version: int
    published_at: dt.datetime
    match_count: int
    changed_matches: list[int]
    # Tylko w odpowiedzi na publikację: {"queued": n, "without_email": [nazwiska]}.
    notifications: dict[str, Any] | None = None


class PublicationRead(PublicationSummary):
    rows: list[dict[str, Any]]
