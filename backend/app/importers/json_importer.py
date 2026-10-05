import json

from pydantic import ValidationError

from app.importers.base import MatchImporter, MatchImportRecord


class ImportFormatError(ValueError):
    pass


class JSONMatchImporter(MatchImporter):
    """Import z JSON: lista obiektów lub ``{"matches": [...]}``."""

    source_name = "json"

    def __init__(self, content: str | bytes) -> None:
        self.content = content

    def fetch_matches(self) -> list[MatchImportRecord]:
        try:
            data = json.loads(self.content)
        except json.JSONDecodeError as exc:
            raise ImportFormatError(f"Niepoprawny JSON: {exc}") from exc
        if isinstance(data, dict):
            data = data.get("matches", [])
        if not isinstance(data, list):
            raise ImportFormatError("Oczekiwano listy meczów")
        records = []
        for i, item in enumerate(data, start=1):
            try:
                records.append(MatchImportRecord(**item))
            except (ValidationError, TypeError) as exc:
                raise ImportFormatError(f"Rekord {i}: {exc}") from exc
        return records
