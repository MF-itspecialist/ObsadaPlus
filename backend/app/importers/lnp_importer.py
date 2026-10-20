"""Import terminarza z Łączy Nas Piłka (laczynaspilka.pl).

API terminarza LNP wydaje token dopiero po przejściu Google reCAPTCHA, więc serwer Obsady+
nie pobiera danych sam. Dane zbiera zakładka (bookmarklet) ``tools/lnp-export.js`` uruchomiona
w przeglądarce użytkownika na stronie terminarza; zapisuje plik JSON w formacie::

    {"source": "laczynaspilka.pl", "exportedAt": "...", "season": {...}, "zpn": {...},
     "competitions": [{"leagueGroup": {...}, "league": {...}, "play": {...}, "matches": <surowa odpowiedź API>}]}

Ten moduł zamienia taki plik na ``MatchImportRecord``. Kształt odpowiedzi API nie jest
udokumentowany, dlatego pola odczytujemy tolerancyjnie (kilka możliwych nazw kluczy).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Iterator
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from app.importers.base import MatchImporter, MatchImportRecord
from app.importers.json_importer import ImportFormatError

LNP_SOURCE = "laczynaspilka.pl"
TZ = ZoneInfo("Europe/Warsaw")

# Rozgrywki poza zakresem „IV liga – juniorzy D2”: szczebel centralny, najmłodsze roczniki, inne dyscypliny.
EXCLUDED = re.compile(
    r"ekstraklas|\bI{1,3}\s*lig|centraln|\b[EFG]\s*-?\s*[12]\b|orlik|żak|skrzat|futsal|plażow|beach|"
    r"kobiet|dziewcz|puchar",
    re.IGNORECASE,
)
# Liczba sędziów wg szczebla: pierwsze dopasowanie wygrywa, reszta dostaje DEFAULT_REFEREES.
REFEREES_BY_LEVEL: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"\b(IV|V)\s*lig|okręgow", re.IGNORECASE), 3),
]
DEFAULT_REFEREES = 1

_HOST_KEYS = ("host", "hostTeam", "homeTeam", "hostName", "home")
_GUEST_KEYS = ("guest", "guestTeam", "awayTeam", "guestName", "away")
_NAME_KEYS = ("name", "fullName", "teamName", "displayName", "shortName", "abbreviation")
_DATETIME_KEYS = ("dateTime", "matchDateTime", "startDateTime", "date", "matchDate", "startDate")
_CANCELLED = re.compile(r"odwoł|przełoż|cancel|postpon", re.IGNORECASE)


def _first(d: dict, keys: tuple[str, ...]) -> Any:
    for k in keys:
        if d.get(k) not in (None, ""):
            return d[k]
    return None


def _name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        name = _first(value, _NAME_KEYS)
        if isinstance(name, str) and name.strip():
            return name.strip()
        for nested in ("team", "club", "squad"):
            if isinstance(value.get(nested), dict):
                return _name(value[nested])
    return None


def _looks_like_match(d: dict) -> bool:
    return _first(d, _HOST_KEYS) is not None and _first(d, _GUEST_KEYS) is not None


def iter_raw_matches(raw: Any) -> Iterator[dict]:
    """Wyciąga obiekty meczów z odpowiedzi API niezależnie od grupowania (kolejki, rundy, strony)."""
    if isinstance(raw, list):
        for item in raw:
            yield from iter_raw_matches(item)
    elif isinstance(raw, dict):
        if _looks_like_match(raw):
            yield raw
            return
        for value in raw.values():
            if isinstance(value, (list, dict)):
                yield from iter_raw_matches(value)


def _parse_datetime(m: dict) -> dt.datetime | None:
    value = _first(m, _DATETIME_KEYS)
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(TZ).replace(tzinfo=None)
    time = m.get("time")
    if isinstance(time, str) and re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", time.strip()) and parsed.time() == dt.time(0):
        parsed = dt.datetime.combine(parsed.date(), dt.time.fromisoformat(time.strip().zfill(5)))
    return parsed


def _venue(m: dict, home_team: str) -> tuple[str, str, str]:
    """(nazwa, miasto, adres) obiektu; bez danych o boisku — boisko gospodarza."""
    stadium = m.get("stadium") or m.get("venue") or m.get("pitch")
    if isinstance(stadium, dict):
        name = _first(stadium, ("facilityName", "name", "stadiumName"))
        city = _first(stadium, ("cityName", "city", "town")) or ""
        address = _first(stadium, ("address", "street", "streetName")) or ""
        if isinstance(name, str) and name.strip():
            return name.strip(), str(city).strip(), str(address).strip()
    name = _first(m, ("stadiumName", "venueName", "pitchName", "place"))
    if isinstance(name, str) and name.strip():
        return name.strip(), str(m.get("cityName") or m.get("city") or "").strip(), ""
    return home_team, "", ""


def _league_label(league: str, play: str) -> str:
    label = league if not play or play.lower() in league.lower() else f"{league} – {play}"
    return label[:100]


def required_referees_for(league: str) -> int:
    for pattern, count in REFEREES_BY_LEVEL:
        if pattern.search(league):
            return count
    return DEFAULT_REFEREES


class LNPMatchImporter(MatchImporter):
    """Mecze z pliku eksportu terminarza LNP; domyślnie tylko nadchodzące (od dziś).

    ``include_past=True`` wczytuje też mecze rozegrane (np. sezon 2025/26 jako dane robocze).
    """

    source_name = "lnp"

    def __init__(
        self, content: str | bytes | dict, date_from: dt.date | None = None, include_past: bool = False
    ) -> None:
        self.content = content
        self.date_from = None if include_past else (date_from or dt.datetime.now(TZ).date())
        self.warnings: list[str] = []

    @staticmethod
    def is_lnp_export(data: Any) -> bool:
        return isinstance(data, dict) and data.get("source") == LNP_SOURCE

    def _load(self) -> dict:
        if isinstance(self.content, dict):
            data = self.content
        else:
            try:
                data = json.loads(self.content)
            except json.JSONDecodeError as exc:
                raise ImportFormatError(f"Niepoprawny JSON: {exc}") from exc
        if not self.is_lnp_export(data) or not isinstance(data.get("competitions"), list):
            raise ImportFormatError("To nie jest plik eksportu terminarza Łączy Nas Piłka")
        return data

    def fetch_matches(self) -> list[MatchImportRecord]:
        records: dict[str, MatchImportRecord] = {}
        skipped_no_time = 0
        for comp in self._load()["competitions"]:
            league = _name(comp.get("league")) or ""
            play = _name(comp.get("play")) or ""
            group = _name(comp.get("leagueGroup")) or ""
            if EXCLUDED.search(f"{group} {league} {play}"):
                continue
            label = _league_label(league, play)
            for m in iter_raw_matches(comp.get("matches")):
                record = self._record(m, label)
                if record is None:
                    continue
                if record == "no-time":
                    skipped_no_time += 1
                    continue
                records[record.external_id or f"{len(records)}"] = record
        if skipped_no_time:
            self.warnings.append(f"Pominięto {skipped_no_time} meczów bez ustalonej godziny rozpoczęcia")
        return sorted(records.values(), key=lambda r: (r.date, r.start_time, r.league))

    def _record(self, m: dict, league: str) -> MatchImportRecord | str | None:
        home, away = _name(_first(m, _HOST_KEYS)), _name(_first(m, _GUEST_KEYS))
        when = _parse_datetime(m)
        if not home or not away or when is None or (self.date_from and when.date() < self.date_from):
            return None
        state = " ".join(str(m.get(k) or "") for k in ("state", "stateTranslation", "status"))
        if _CANCELLED.search(state):
            return None
        if when.time() == dt.time(0):
            return "no-time"
        venue_name, venue_city, venue_address = _venue(m, home)
        match_id = _first(m, ("id", "matchId", "uuid"))
        try:
            return MatchImportRecord(
                external_id=f"lnp:{match_id}" if match_id else None,
                date=when.date(),
                start_time=when.time(),
                league=league,
                home_team=home[:200],
                away_team=away[:200],
                venue_name=venue_name[:200],
                venue_city=venue_city[:100] or None,
                venue_address=venue_address[:255] or None,
                required_referees=required_referees_for(league),
            )
        except ValidationError as exc:
            self.warnings.append(f"{home} – {away}: {exc.errors()[0]['msg']}")
            return None
