"""Import meczów. ``MatchImporter`` to interfejs; kolejne źródła (strona komisji) to nowe podklasy."""

from app.importers.base import MatchImporter, MatchImportRecord
from app.importers.csv_importer import CSVMatchImporter
from app.importers.json_importer import JSONMatchImporter
from app.importers.manual_importer import ManualMatchImporter

__all__ = [
    "CSVMatchImporter",
    "JSONMatchImporter",
    "ManualMatchImporter",
    "MatchImportRecord",
    "MatchImporter",
]
