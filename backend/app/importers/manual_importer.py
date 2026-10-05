from app.importers.base import MatchImporter, MatchImportRecord


class ManualMatchImporter(MatchImporter):
    """Mecze przekazane bezpośrednio jako lista rekordów (np. z formularza lub testów)."""

    source_name = "manual"

    def __init__(self, records: list[MatchImportRecord | dict]) -> None:
        self._records = [r if isinstance(r, MatchImportRecord) else MatchImportRecord(**r) for r in records]

    def fetch_matches(self) -> list[MatchImportRecord]:
        return list(self._records)
