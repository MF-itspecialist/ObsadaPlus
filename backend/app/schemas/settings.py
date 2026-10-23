from typing import Literal

from pydantic import BaseModel, Field


class SystemSettings(BaseModel):
    """Ustawienia edytowalne w UI. Domyślne wartości = specyfikacja MVP."""

    transport_safety_buffer_minutes: int = Field(15, ge=0, le=180)
    # Przyjazd przed meczem — bufor generatora, wspólny dla wszystkich meczów.
    arrival_before_minutes: int = Field(45, ge=0, le=240)
    # Generator przydziela sędziemu najwyżej tyle meczów dziennie; więcej tylko ręcznie.
    generator_max_matches_per_day: int = Field(3, ge=1, le=10)
    # Jak mocno kierować sędzie z licencją kobiecą najpierw na mecze kobiet.
    women_priority_penalty: float = Field(30.0, ge=0)
    # Zespół G + A1 + A2: jak mocno dobierać sędziów, którzy mogą dojechać razem (km wspólnej trasy).
    crew_route_weight: float = Field(1.0, ge=0)
    # Kara za mecz spoza preferowanych lig sędziego i za mecz klubu, którego sędzia unika.
    preferred_league_penalty: float = Field(25.0, ge=0)
    avoided_club_penalty: float = Field(150.0, ge=0)
    distance_weight: float = Field(2.0, ge=0)
    travel_time_weight: float = Field(0.5, ge=0)
    daily_match_weight: float = Field(20.0, ge=0)
    weekend_match_weight: float = Field(10.0, ge=0)
    workload_balance_weight: float = Field(10.0, ge=0)
    within_preferred_factor: float = Field(0.25, ge=0)
    over_preferred_factor: float = Field(1.5, ge=0)
    # [[górna granica km, kara], ...] — ostatni próg dotyczy wszystkiego powyżej.
    distance_brackets: list[tuple[float, float]] = [
        (10, 0),
        (20, 10),
        (30, 30),
        (50, 70),
        (75, 150),
        (100000, 300),
    ]
    assume_available_without_entry: bool = False
    # Metoda obsady: „cpsat” rozważa cały okres naraz (OR-Tools), „greedy” mecz po meczu.
    optimizer: Literal["greedy", "cpsat"] = "cpsat"
    optimizer_time_limit_s: int = Field(15, ge=1, le=120)
    # Parametry HaversineRoutingService.
    routing_road_factor: float = Field(1.3, ge=1.0, le=3.0)
    routing_avg_speed_kmh: float = Field(40.0, gt=0, le=150)
    # Stawka kilometrówki (zł za km) — domyślnie samochód osobowy powyżej 900 cm³.
    mileage_rate: float = Field(0.8358, ge=0, le=10)
    # Domyślny czas meczu przy imporcie bez godziny zakończenia.
    default_match_duration_minutes: int = Field(105, ge=30, le=300)
