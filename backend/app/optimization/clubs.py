"""Porównywanie nazw klubów (konflikt interesów, unikane kluby).

Wpis „Agape Białołęka” pasuje do drużyn „Agape Białołęka” i „Agape II Białołęka (Warszawa)”;
krótszy wpis „Agape” — do każdej drużyny, w której nazwie jest to słowo.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

_ROMAN = re.compile(r"^(i{1,3}|iv|v|vi)$")


@lru_cache(maxsize=4096)
def club_tokens(name: str) -> frozenset[str]:
    """Słowa nazwy bez polskich znaków, nawiasów i numeru zespołu (II, III…)."""
    text = unicodedata.normalize("NFKD", name.casefold().replace("ł", "l"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    words = re.findall(r"[a-z0-9]+", text)
    return frozenset(w for w in words if not _ROMAN.match(w))


def club_matches(entry: str, team: str) -> bool:
    wanted = club_tokens(entry)
    return bool(wanted) and wanted <= club_tokens(team)


def matching_club(entries: tuple[str, ...], *teams: str) -> str | None:
    """Pierwszy wpis z listy pasujący do którejś z drużyn (np. gospodarza lub gościa)."""
    for entry in entries:
        if any(club_matches(entry, t) for t in teams):
            return entry
    return None
