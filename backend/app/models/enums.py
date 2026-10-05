"""Wyliczenia domenowe współdzielone przez modele, schematy i silnik optymalizacji."""

from enum import Enum


class RefereeRole(str, Enum):
    """Rola w zespole sędziowskim. MVP obsadza tylko MAIN."""

    MAIN = "MAIN"
    ASSISTANT_1 = "ASSISTANT_1"
    ASSISTANT_2 = "ASSISTANT_2"
    FOURTH = "FOURTH"
    OBSERVER = "OBSERVER"


# Kolejność ról wynikająca z liczby wymaganych sędziów (required_referees).
ROLE_ORDER: tuple[RefereeRole, ...] = (
    RefereeRole.MAIN,
    RefereeRole.ASSISTANT_1,
    RefereeRole.ASSISTANT_2,
    RefereeRole.FOURTH,
)


def roles_for(required_referees: int) -> list[RefereeRole]:
    """Mapuje liczbę wymaganych sędziów na listę ról do obsadzenia."""
    n = max(0, min(required_referees, len(ROLE_ORDER)))
    return list(ROLE_ORDER[:n])


class MatchStatus(str, Enum):
    UNASSIGNED = "UNASSIGNED"
    PARTIALLY_ASSIGNED = "PARTIALLY_ASSIGNED"
    ASSIGNED = "ASSIGNED"
    CANCELLED = "CANCELLED"


class GenerationRunStatus(str, Enum):
    PREVIEW = "PREVIEW"
    CONFIRMED = "CONFIRMED"
    DISCARDED = "DISCARDED"


class GenerationMode(str, Enum):
    """KEEP_MANUAL – zachowaj ręczne przypisania; FULL – generuj całość od nowa."""

    KEEP_MANUAL = "KEEP_MANUAL"
    FULL = "FULL"
