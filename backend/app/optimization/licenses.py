"""Uprawnienia licencji sędziowskich — JEDNO miejsce do poprawek.

Każda licencja mówi, do jakiego poziomu rozgrywek sędzia może prowadzić mecz
jako sędzia główny (``main``) i jako asystent (``assistant``) — osobno dla
piłki seniorów i młodzieży, piłki kobiet i futsalu. Generator blokuje sędziów
bez wystarczającej licencji; admin może przypisać ręcznie (z ostrzeżeniem).

Reguły oznaczone ``assumption`` to założenia do weryfikacji z Komisją Sędziowską.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from app.models.enums import RefereeRole


class Category(str, Enum):
    MEN = "MEN"  # piłka seniorów i młodzieży (11-osobowa)
    WOMEN = "WOMEN"
    FUTSAL = "FUTSAL"  # futsal i piłka plażowa


# Poziomy rozgrywek (wyższa liczba = wyższa liga).
YOUTH, KLASA_B, KLASA_A, OKREGOWA, V_LIGA, IV_LIGA, III_LIGA, II_LIGA, I_LIGA, EKSTRAKLASA = range(1, 11)
W_NIZSZE, W_II_LIGA, W_I_LIGA, W_EKSTRALIGA = range(1, 5)
F_NIZSZE, F_I_LIGA, F_EKSTRAKLASA = range(1, 4)

LEVEL_NAMES: dict[Category, dict[int, str]] = {
    Category.MEN: {
        YOUTH: "rozgrywki młodzieżowe", KLASA_B: "klasa B", KLASA_A: "klasa A", OKREGOWA: "klasa okręgowa",
        V_LIGA: "V liga", IV_LIGA: "IV liga", III_LIGA: "III liga", II_LIGA: "II liga", I_LIGA: "I liga",
        EKSTRAKLASA: "Ekstraklasa",
    },
    Category.WOMEN: {W_NIZSZE: "III/IV liga kobiet", W_II_LIGA: "II liga kobiet", W_I_LIGA: "I liga kobiet",
                     W_EKSTRALIGA: "Ekstraliga kobiet"},
    Category.FUTSAL: {F_NIZSZE: "niższe ligi futsalu", F_I_LIGA: "I liga futsal", F_EKSTRAKLASA: "Ekstraklasa futsal"},
}


@dataclass(frozen=True)
class LicenseRule:
    group: str
    # kategoria → najwyższy poziom; brak kategorii = brak uprawnień
    main: dict[Category, int] = field(default_factory=dict)
    assistant: dict[Category, int] = field(default_factory=dict)
    assumption: str | None = None


def _men(main: int | None, assistant: int | None) -> tuple[dict[Category, int], dict[Category, int]]:
    return ({Category.MEN: main} if main else {}), ({Category.MEN: assistant} if assistant else {})


def _rule(group: str, main: int | None, assistant: int | None, assumption: str | None = None) -> LicenseRule:
    m, a = _men(main, assistant)
    return LicenseRule(group, m, a, assumption)


SEDZIOWIE, ASYSTENCI, KOBIETY, FUTSAL = "Sędziowie", "Asystenci", "Piłka kobiet", "Futsal i piłka plażowa"
WOMEN_TO_MEN_ASSUMPTION = "poziom meczów męskich wg tabeli przeliczenia (do weryfikacji)"

# ---------------------------------------------------------------------------
# TABELA LICENCJI. Kolejność = kolejność w formularzu sędziego.
# Sędzia z licencją do okręgówki lub niżej jako asystent: max klasa okręgowa;
# z licencją wyższą jako asystent: max III liga — wyżej tylko licencje asystenckie.
# ---------------------------------------------------------------------------
LICENSE_RULES: dict[str, LicenseRule] = {
    "Sędzia TopAmator A (w tym zawodowi)": _rule(SEDZIOWIE, EKSTRAKLASA, III_LIGA),
    "Sędzia TopAmator B": _rule(SEDZIOWIE, II_LIGA, III_LIGA),
    "Sędzia III liga (TopAmator C)": _rule(SEDZIOWIE, III_LIGA, III_LIGA),
    "Sędzia IV liga": _rule(SEDZIOWIE, IV_LIGA, III_LIGA),
    "Sędzia V liga": _rule(SEDZIOWIE, V_LIGA, III_LIGA),
    "Sędzia klasa okręgowa": _rule(SEDZIOWIE, OKREGOWA, OKREGOWA),
    "Sędzia klasa A": _rule(SEDZIOWIE, KLASA_A, OKREGOWA),
    "Sędzia klasa B": _rule(SEDZIOWIE, KLASA_B, OKREGOWA),
    "Sędzia próbny (C)": _rule(SEDZIOWIE, YOUTH, OKREGOWA),
    "Asystent zawodowy": _rule(ASYSTENCI, None, EKSTRAKLASA),
    "Asystent s.c. (niezawodowy)": _rule(ASYSTENCI, None, I_LIGA),
    "Asystent III/IV/V liga (w tym asystenci mazowieccy)": _rule(ASYSTENCI, None, IV_LIGA),
    "Asystent okręgowy / pozostali": _rule(ASYSTENCI, None, OKREGOWA),
    # Sędzie mogą prowadzić też mecze męskie (poziom z tabeli przeliczenia niżej),
    # ale generator kieruje je najpierw na mecze kobiet (miękka preferencja w SCORE).
    "Sędzia Ekstraliga kobiet": LicenseRule(
        KOBIETY, {Category.WOMEN: W_EKSTRALIGA}, {Category.WOMEN: W_EKSTRALIGA}, assumption=WOMEN_TO_MEN_ASSUMPTION
    ),
    "Sędzia I liga kobiet": LicenseRule(
        KOBIETY, {Category.WOMEN: W_I_LIGA}, {Category.WOMEN: W_I_LIGA}, assumption=WOMEN_TO_MEN_ASSUMPTION
    ),
    "Sędzia II liga kobiet / asystentka s.c.": LicenseRule(
        KOBIETY, {Category.WOMEN: W_II_LIGA}, {Category.WOMEN: W_EKSTRALIGA},
        assumption=f"główna do II ligi kobiet, asystentka do Ekstraligi kobiet; {WOMEN_TO_MEN_ASSUMPTION}",
    ),
    "Sędzia Ekstraklasa futsal i piłka plażowa": LicenseRule(
        FUTSAL, {Category.FUTSAL: F_EKSTRAKLASA}, {Category.FUTSAL: F_EKSTRAKLASA}
    ),
    "Sędzia I liga futsal i piłka plażowa": LicenseRule(
        FUTSAL, {Category.FUTSAL: F_I_LIGA}, {Category.FUTSAL: F_I_LIGA}
    ),
}

# Przeliczenie poziomów między piłką męską a kobiecą (w obie strony):
# licencja „męska” do poziomu X → mecze kobiet do poziomu Y i odwrotnie.
# ZAŁOŻENIE do weryfikacji z Komisją Sędziowską.
MEN_TO_WOMEN: tuple[tuple[int, int], ...] = ((III_LIGA, W_EKSTRALIGA), (V_LIGA, W_I_LIGA), (KLASA_A, W_II_LIGA), (YOUTH, W_NIZSZE))


# --- rozpoznawanie poziomu meczu z nazwy ligi -----------------------------------
_YOUTH = re.compile(r"junior|trampkarz|młodzik|mlodzik|orlik|żak|skrzat|\bu-?\d{1,2}\b|młodzież|ekstraliga", re.I)
_ROMAN = {"i": I_LIGA, "ii": II_LIGA, "iii": III_LIGA, "iv": IV_LIGA, "v": V_LIGA}
_WORDS = {"pierwsza": I_LIGA, "druga": II_LIGA, "trzecia": III_LIGA, "czwarta": IV_LIGA, "piąta": V_LIGA}


def _numbered_liga(text: str) -> int | None:
    m = re.search(r"\b(i{1,3}|iv|v)\s+liga\b", text)
    if m:
        return _ROMAN[m[1]]
    m = re.search(r"\b(pierwsza|druga|trzecia|czwarta|piąta)\s+liga\b", text)
    return _WORDS[m[1]] if m else None


def classify_league(league: str) -> tuple[Category, int] | None:
    """Kategoria i poziom meczu na podstawie nazwy ligi; ``None`` = nieznany (bez kontroli licencji)."""
    text = league.lower().strip()
    if not text:
        return None
    if "futsal" in text or "plażow" in text:
        if "ekstraklasa" in text:
            return Category.FUTSAL, F_EKSTRAKLASA
        return Category.FUTSAL, F_I_LIGA if _numbered_liga(text) == I_LIGA else F_NIZSZE
    if "kobiet" in text:
        if "ekstraliga" in text:
            return Category.WOMEN, W_EKSTRALIGA
        n = _numbered_liga(text)
        return Category.WOMEN, {I_LIGA: W_I_LIGA, II_LIGA: W_II_LIGA}.get(n, W_NIZSZE)
    if _YOUTH.search(text):
        return Category.MEN, YOUTH
    if "ekstraklasa" in text:
        return Category.MEN, EKSTRAKLASA
    if "okręgow" in text or "okregow" in text:
        return Category.MEN, OKREGOWA
    n = _numbered_liga(text)
    if n:
        return Category.MEN, n
    if re.search(r"klasa\s*a\b", text):
        return Category.MEN, KLASA_A
    if re.search(r"klasa\s*[bc]\b", text):
        return Category.MEN, KLASA_B
    return None


# --- sprawdzenie uprawnień ---------------------------------------------------------
def _is_assistant(role: RefereeRole) -> bool:
    return role in (RefereeRole.ASSISTANT_1, RefereeRole.ASSISTANT_2)


def max_level(licenses: list[str] | tuple[str, ...], category: Category, role: RefereeRole) -> int:
    """Najwyższy poziom, do którego licencje uprawniają w danej kategorii i roli (0 = brak)."""
    best = 0
    for name in licenses:
        rule = LICENSE_RULES.get(name)
        if rule is None:
            continue
        levels = rule.assistant if _is_assistant(role) else rule.main
        best = max(best, levels.get(category, 0))
        if category == Category.WOMEN:
            men = levels.get(Category.MEN, 0)
            best = max(best, next((w for threshold, w in MEN_TO_WOMEN if men >= threshold), 0))
        elif category == Category.MEN:
            women = levels.get(Category.WOMEN, 0)
            best = max(best, next((m for m, w in MEN_TO_WOMEN if women >= w), 0))
    return best


def has_women_license(licenses: list[str] | tuple[str, ...]) -> bool:
    return any(Category.WOMEN in LICENSE_RULES[n].main for n in licenses if n in LICENSE_RULES)


def is_women_match(league: str) -> bool:
    match = classify_league(league)
    return match is not None and match[0] == Category.WOMEN


def check_license(licenses: list[str] | tuple[str, ...], league: str, role: RefereeRole) -> str | None:
    """``None`` gdy sędzia ma uprawnienia; w przeciwnym razie powód odmowy dla admina."""
    if role == RefereeRole.OBSERVER:
        return None
    match = classify_league(league)
    if match is None:
        return None
    category, level = match
    allowed = max_level(licenses, category, role)
    if allowed >= level:
        return None
    role_name = "asystent" if _is_assistant(role) else "sędzia główny"
    if not licenses:
        return f"brak przydzielonej licencji (mecz: {LEVEL_NAMES[category][level]})"
    if allowed == 0:
        return f"licencja nie uprawnia do meczu {LEVEL_NAMES[category][level]} jako {role_name}"
    return (
        f"licencja jako {role_name} do: {LEVEL_NAMES[category][allowed]}, "
        f"mecz: {LEVEL_NAMES[category][level]}"
    )


def license_catalog() -> list[dict]:
    """Licencje pogrupowane do formularza (z opisem uprawnień)."""
    groups: dict[str, list[dict]] = {}
    for name, rule in LICENSE_RULES.items():
        parts = []
        for label, levels in (("główny", rule.main), ("asystent", rule.assistant)):
            for cat, lvl in levels.items():
                parts.append(f"{label}: do {LEVEL_NAMES[cat][lvl]}")
            women = levels.get(Category.WOMEN)
            if women and Category.MEN not in levels:
                men = next((m for m, w in MEN_TO_WOMEN if women >= w), 0)
                parts.append(f"{label} (mecze męskie): do {LEVEL_NAMES[Category.MEN][men]}")
        groups.setdefault(rule.group, []).append(
            {"name": name, "scope": "; ".join(parts), "assumption": rule.assumption}
        )
    return [{"title": title, "licenses": items} for title, items in groups.items()]
