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
    # Trasy: "auto" (Google, gdy jest klucz → OSRM, gdy jest OSRM_URL → szacunek), "google", "osrm", "haversine".
    routing_provider: str = "auto"
    # Klucz Google Maps (Geocoding API + Routes API). Pusty = OpenStreetMap (Nominatim) i OSRM.
    google_maps_api_key: str = ""
    # Klucz tylko do wyszukiwania stadionów w Google Maps (Places API) — nie przełącza tras na Google.
    google_places_api_key: str = ""
    # Adres serwera OSRM, np. http://osrm:5000 w docker-compose. Pusty = bez OSRM.
    osrm_url: str = ""
    # Obszar preferowany przy wyszukiwaniu adresów ("lon1,lat1,lon2,lat2"; domyślnie woj. mazowieckie).
    geocoding_viewbox: str = "19.2,53.5,23.2,51.0"
    # Czy przy starcie aplikacji tworzyć tabele / wypełniać danymi testowymi.
    auto_create_tables: bool = True
    seed_on_startup: bool = False
    # Logowanie: ważność sesji i ciasteczko. COOKIE_SECURE=true, gdy aplikacja działa po HTTPS.
    session_days: int = 30
    cookie_secure: bool = False
    # Harmonogram w tle (automatyczny import meczów). W testach wyłączony.
    scheduler_enabled: bool = True
    # Pierwsze konto obsadzającego — tworzone przy starcie, gdy w bazie nie ma żadnego użytkownika.
    admin_login: str = "admin"
    admin_password: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()
