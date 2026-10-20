"""Import terminarza rozgrywek seniorskich regionu z 90minut.pl.

Strona regionu (np. ``ligireg.php?id_sezon=109&id_okreg=6`` — Mazowsze, sezon 2026/27)
zawiera listę lig (IV liga … klasa B), a strona ligi — kolejki z meczami:
gospodarz, wynik, gość, „9 sierpnia, 15:00” i opcjonalnie notę „na stadionie …”.

* mecze bez daty lub godziny (przyszłe kolejki) są pomijane z ostrzeżeniem,
* boisko: z noty „na stadionie/boisku …”, inaczej boisko gospodarza (lokalizacja
  miejscowości z nazwy drużyny — przybliżona),
* ``external_id`` = ``90minut:<id ligi>:<skrót par drużyn>``, więc ponowny import aktualizuje mecze.

    python -m app.importers.m90_importer --season 109 --region 6
"""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import re
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from app.importers.base import MatchImporter, MatchImportRecord
from app.importers.lnp_importer import required_referees_for

BASE_URL = "http://www.90minut.pl"
USER_AGENT = "Mozilla/5.0 (compatible; ObsadaPlus/0.1)"
MONTHS = {
    "stycznia": 1, "lutego": 2, "marca": 3, "kwietnia": 4, "maja": 5, "czerwca": 6, "lipca": 7,
    "sierpnia": 8, "września": 9, "października": 10, "listopada": 11, "grudnia": 12,
}
SENIOR = re.compile(r"\b(IV liga|V liga|Liga okręgowa|Klasa [ABC])\b", re.IGNORECASE)
SPONSORS = re.compile(r"^(Decathlon|Keeza)\s+", re.IGNORECASE)
_LEAGUE_LINK = re.compile(r'href="/liga/1/liga(\d+)\.html"[^>]*>([^<]+)</a>')
_ROW = re.compile(
    r'<tr align="left">\s*<td nowrap valign="top" width="180">(.*?)</td>\s*'
    r'<td nowrap valign="top" align="center" width="50">.*?</td>\s*'
    r'<td nowrap valign="top" width="180">(.*?)</td>\s*'
    r'<td valign="top" nowrap align="left" width="190">(.*?)</td>\s*</tr>'
    r'(?:\s*<tr align="left">\s*<td colspan="4"><i>(.*?)</i></td>\s*</tr>)?',
    re.S,
)
_DATE = re.compile(r"(\d{1,2})\s+(\w+),\s*(\d{1,2}):(\d{2})")
# Ostatnie człony nazw miejscowości, których nie wolno odcinać ("Grodzisk Mazowiecki").
_TOWN_SUFFIXES = {"mazowiecki", "mazowiecka", "podlaski", "kościelny", "kościelna", "kalwaria", "jeziorna", "szlachecki",
                  "rządowy", "duży", "duża", "duże", "mały", "mała", "małe", "wielki", "wielka", "wielkie", "nowy", "nowa",
                  "nowe", "stary", "stara", "stare", "górny", "górna", "górne", "dolny", "dolna", "dolne", "kolonia"}
_ROMAN = re.compile(r"^(I{1,3}|IV|V|VI)$")


@dataclass(frozen=True)
class League:
    id: int
    name: str  # "IV liga – mazowiecka"


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def league_label(raw: str) -> str:
    """'Keeza Liga okręgowa 2026/2027, grupa: Warszawa I' → 'Liga okręgowa – Warszawa I'."""
    name = SPONSORS.sub("", " ".join(raw.split()))
    name = re.sub(r"\s*\d{4}/\d{4}", "", name)
    base, _, group = name.partition(", grupa:")
    return f"{base.strip()} – {group.strip()}" if group else base.strip()


def parse_region(page: str) -> list[League]:
    """Ligi seniorskie regionu (IV liga, V liga, okręgówka, klasy A–C) ze strony ligireg.php."""
    leagues: dict[int, League] = {}
    for league_id, raw in _LEAGUE_LINK.findall(page):
        raw = html.unescape(raw)
        if SENIOR.search(raw) and "grupa:" in raw:
            leagues[int(league_id)] = League(int(league_id), league_label(raw))
    return list(leagues.values())


def town_from_team(team: str) -> str:
    """Miejscowość z nazwy drużyny: 'Świt II Nowy Dwór Mazowiecki' → 'Nowy Dwór Mazowiecki'.

    'Agape Białołęka (Warszawa)' → 'Białołęka, Warszawa'. Heurystyka — lokalizacja przybliżona.
    """
    m = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", team)
    if m:
        last = m[1].split()[-1] if m[1].split() else ""
        return f"{last}, {m[2]}" if last and last.lower() != m[2].lower() else m[2]
    words = team.split()
    for i in range(len(words) - 1, -1, -1):  # po numerze drużyny (II, III) zostaje miejscowość
        if _ROMAN.match(words[i]) and i < len(words) - 1:
            return " ".join(words[i + 1:])
    if len(words) >= 3 and words[-1].lower() in _TOWN_SUFFIXES:  # "Iskra Zbrosza Duża" → "Zbrosza Duża"
        return " ".join(words[-2:])
    return words[-1] if words else ""


def _venue(note: str, home: str) -> tuple[str, str, str]:
    """(nazwa, miasto, adres) obiektu."""
    m = re.match(r"^na (stadionie|boisku|obiekcie|terenie)\s+(.+)$", note, re.I)
    if m:
        name, _, street = m[2].partition(" przy ")
        label = f"{m[1].capitalize()} {name}".replace("Stadionie", "Stadion").replace("Boisku", "Boisko")
        # Bez ulicy szukamy po nazwie obiektu (np. „Strefy Sportu”); gdy mapa nie zna — środek miejscowości.
        return label[:200], town_from_team(home), street.strip() or name.strip()
    return f"Boisko: {home}"[:200], town_from_team(home), ""


def parse_league(page: str, league: League, season_start_year: int) -> tuple[list[MatchImportRecord], int]:
    """Mecze ligi z datą i godziną oraz liczba pominiętych (brak terminu)."""
    records: list[MatchImportRecord] = []
    skipped = 0
    for home_raw, away_raw, when_raw, note_raw in _ROW.findall(page):
        home, away, when, note = _text(home_raw), _text(away_raw), _text(when_raw), _text(note_raw or "")
        m = _DATE.search(when)
        month = MONTHS.get(m[2].lower()) if m else None
        if not home or not away or not m or month is None:
            skipped += 1
            continue
        year = season_start_year if month >= 7 else season_start_year + 1
        name, city, address = _venue(note, home)
        pair = hashlib.sha1(f"{home}|{away}".encode()).hexdigest()[:12]
        try:
            records.append(
                MatchImportRecord(
                    external_id=f"90minut:{league.id}:{pair}",
                    date=dt.date(year, month, int(m[1])),
                    start_time=dt.time(int(m[3]), int(m[4])),
                    league=league.name[:100],
                    home_team=home[:200],
                    away_team=away[:200],
                    venue_name=name,
                    venue_city=city,
                    venue_address=address,
                    required_referees=required_referees_for(league.name),
                )
            )
        except (ValidationError, ValueError):
            skipped += 1
    return records, skipped


def fetch_page(url: str) -> str:
    resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.content.decode("iso-8859-2", errors="replace")


class M90MatchImporter(MatchImporter):
    """Mecze seniorskie regionu z 90minut.pl (strony pobierane po kolei, z przerwą)."""

    source_name = "90minut"

    def __init__(
        self,
        season_id: int,
        region_id: int,
        season_start_year: int,
        fetch: Callable[[str], str] = fetch_page,
        delay_s: float = 1.0,
    ) -> None:
        self.season_id = season_id
        self.region_id = region_id
        self.season_start_year = season_start_year
        self.fetch = fetch
        self.delay_s = delay_s
        self.warnings: list[str] = []
        self.leagues: list[League] = []

    def fetch_matches(self) -> list[MatchImportRecord]:
        region = self.fetch(f"{BASE_URL}/ligireg.php?id_sezon={self.season_id}&id_okreg={self.region_id}")
        self.leagues = parse_region(region)
        records: list[MatchImportRecord] = []
        skipped_total = 0
        for league in self.leagues:
            time.sleep(self.delay_s)
            found, skipped = parse_league(self.fetch(f"{BASE_URL}/liga/1/liga{league.id}.html"), league, self.season_start_year)
            records += found
            skipped_total += skipped
        if skipped_total:
            self.warnings.append(f"Pominięto {skipped_total} meczów bez ustalonej daty lub godziny (przyszłe kolejki)")
        return records


if __name__ == "__main__":
    import argparse

    from app.database.db import SessionLocal
    from app.importers.import_service import import_matches
    from app.services.geocoding_service import get_geocoder
    from app.services.settings_service import get_settings

    parser = argparse.ArgumentParser(description="Import rozgrywek seniorskich regionu z 90minut.pl")
    parser.add_argument("--season", type=int, default=109, help="id_sezon w 90minut.pl (109 = 2026/27)")
    parser.add_argument("--region", type=int, default=6, help="id_okreg w 90minut.pl (6 = Mazowsze)")
    parser.add_argument("--start-year", type=int, default=2026, help="rok rozpoczęcia sezonu")
    args = parser.parse_args()

    importer = M90MatchImporter(args.season, args.region, args.start_year)
    with SessionLocal() as session:
        result = import_matches(session, importer, get_settings(session).default_match_duration_minutes, get_geocoder())
    print(f"Ligi: {len(importer.leagues)}, dodano: {result['created']}, zaktualizowano: {result['updated']}")
    for line in result["errors"]:
        print(" -", line)
