"""Konfiguracja aplikacji wczytywana ze zmiennych środowiskowych (lub pliku .env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Konfiguracja infrastrukturalna.

    Parametry biznesowe (wagi scoringu, bufor bezpieczeństwa) są w tabeli
    ``system_settings`` i edytuje się je w UI, nie tutaj.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Obsada+"
    # SQLite na dev; w docker-compose ustawiane na PostgreSQL.
    database_url: str = "sqlite:///./obsada.db"
    # Dozwolone originy frontendu (CORS), rozdzielone przecinkami.
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    # Implementacja RoutingService: "haversine" (MVP). Później: "osrm", "google".
    routing_provider: str = "haversine"
    # Klucz Google Maps (Geocoding API). Pusty = geokodowanie przez OpenStreetMap (Nominatim).
    google_maps_api_key: str = ""
    # Obszar preferowany przy wyszukiwaniu adresów ("lon1,lat1,lon2,lat2"; domyślnie woj. mazowieckie).
    geocoding_viewbox: str = "19.2,53.5,23.2,51.0"
    # Czy przy starcie aplikacji tworzyć tabele / wypełniać danymi testowymi.
    auto_create_tables: bool = True
    seed_on_startup: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()
