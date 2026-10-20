"""Import meczów. ``MatchImporter`` to interfejs; każde źródło (plik, eksport z LNP) to podklasa."""

from app.importers.base import MatchImporter, MatchImportRecord
from app.importers.csv_importer import CSVMatchImporter
from app.importers.json_importer import JSONMatchImporter
from app.importers.lnp_importer import LNPMatchImporter
from app.importers.manual_importer import ManualMatchImporter

__all__ = [
    "CSVMatchImporter",
    "JSONMatchImporter",
    "LNPMatchImporter",
    "ManualMatchImporter",
    "MatchImportRecord",
    "MatchImporter",
]
