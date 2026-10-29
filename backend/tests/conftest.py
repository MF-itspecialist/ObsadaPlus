"""Konfiguracja testów API: baza SQLite w pamięci, osobna dla każdego testu."""

import os

os.environ.setdefault("AUTO_CREATE_TABLES", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.database.db import Base, create_db_engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.geocoding_service import Geocoder, get_geocoder  # noqa: E402


class OfflineGeocoder(Geocoder):
    """Domyślny geokoder testów: nie łączy się z internetem i niczego nie znajduje."""

    name = "offline"

    def geocode(self, address: str, city: str):
        return None


@pytest.fixture()
def db_session():
    engine = create_db_engine("sqlite://")
    engine.pool = StaticPool(engine.pool._creator)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield Session
    engine.dispose()


ADMIN_LOGIN, ADMIN_PASSWORD = "admin", "haslo-testowe-123"


@pytest.fixture()
def anon_client(db_session):
    """Klient bez logowania (konto obsadzającego istnieje w bazie)."""
    from app.models import UserRole
    from app.services import auth_service

    def _get_db():
        db = db_session()
        try:
            yield db
        finally:
            db.close()

    with db_session() as db:
        auth_service.create_user(db, ADMIN_LOGIN, ADMIN_PASSWORD, UserRole.ADMIN, "Obsadzający")
    auth_service.throttle = auth_service.LoginThrottle()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_geocoder] = OfflineGeocoder
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def client(anon_client):
    """Klient zalogowany jako obsadzający."""
    r = anon_client.post("/api/auth/login", json={"login": ADMIN_LOGIN, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return anon_client


@pytest.fixture()
def seeded_client(client, db_session):
    from app.database.seed import seed_database

    with db_session() as db:
        seed_database(db)
    return client
