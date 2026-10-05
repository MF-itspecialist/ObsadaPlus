"""Silnik generowania obsady.

Moduł jest niezależny od bazy danych i FastAPI: operuje na obiektach z
``domain.py``. Dzięki temu można go testować jednostkowo i wymieniać strategię
(zachłanny scoring → OR-Tools / CP-SAT) bez zmian w reszcie aplikacji.
"""

from app.optimization.domain import (
    AvailabilityEntry,
    FixedBooking,
    OptimizationSettings,
    Problem,
    RefereeProfile,
    Slot,
)
from app.optimization.generator import AssignmentGenerator, GenerationResult

__all__ = [
    "AssignmentGenerator",
    "AvailabilityEntry",
    "FixedBooking",
    "GenerationResult",
    "OptimizationSettings",
    "Problem",
    "RefereeProfile",
    "Slot",
]
