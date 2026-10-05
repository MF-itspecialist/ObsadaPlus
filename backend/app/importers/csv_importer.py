import csv
import io

from pydantic import ValidationError

from app.importers.base import MatchImporter, MatchImportRecord
from app.importers.json_importer import ImportFormatError


class CSVMatchImporter(MatchImporter):
    """Import z CSV z nagłówkiem o nazwach pól ``MatchImportRecord`` (separator , lub ;)."""

    source_name = "csv"

    def __init__(self, content: str | bytes) -> None:
        self.content = content.decode("utf-8-sig") if isinstance(content, bytes) else content

    def fetch_matches(self) -> list[MatchImportRecord]:
        sample = self.content[:2048]
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
        reader = csv.DictReader(io.StringIO(self.content), delimiter=delimiter)
        records = []
        for i, row in enumerate(reader, start=2):
            clean = {k.strip(): v.strip() for k, v in row.items() if k and v not in (None, "")}
            try:
                records.append(MatchImportRecord(**clean))
            except ValidationError as exc:
                raise ImportFormatError(f"Wiersz {i}: {exc}") from exc
        return records
