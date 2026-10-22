"""Podokręgi Mazowieckiego ZPN — do filtrowania sędziów, meczów i obiektów.

Podokręg sędziego bierzemy z dopisku w notatkach („podokręg Płock”), a gdy go
nie ma — przyjmujemy podokręg z najbliższą siedzibą (przybliżenie granic).
"""

from __future__ import annotations

# siedziba podokręgu: (szerokość, długość)
REGION_SEATS: dict[str, tuple[float, float]] = {
    "Warszawa": (52.2297, 21.0122),
    "Płock": (52.5463, 19.7065),
    "Radom": (51.4027, 21.1471),
    "Siedlce": (52.1676, 22.2902),
    "Ciechanów": (52.8810, 20.6200),
    "Ostrołęka": (53.0840, 21.5750),
}
REGIONS = tuple(REGION_SEATS)
_TAG = "podokręg "


def nearest_region(latitude: float | None, longitude: float | None) -> str:
    if latitude is None or longitude is None:
        return ""
    # stopień długości geograficznej na Mazowszu ≈ 0,62 stopnia szerokości
    return min(
        REGION_SEATS,
        key=lambda r: (REGION_SEATS[r][0] - latitude) ** 2 + ((REGION_SEATS[r][1] - longitude) * 0.62) ** 2,
    )


def region_for(latitude: float | None, longitude: float | None, notes: str | None = None) -> str:
    tagged = (notes or "").rpartition(_TAG)[2].strip()
    if _TAG in (notes or "") and tagged in REGION_SEATS:
        return tagged
    return nearest_region(latitude, longitude)
