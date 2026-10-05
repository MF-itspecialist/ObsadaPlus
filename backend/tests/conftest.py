"""Konfiguracja testów API: baza SQLite w pamięci, osobna dla każdego testu."""

import os

os.environ.setdefault("AUTO_CREATE_TABLES", "false")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.database.db import Base, create_db_engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def db_session():
    engine = create_db_engine("sqlite://")
    engine.pool = StaticPool(engine.pool._creator)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield Session
    engine.dispose()


@pytest.fixture()
def client(db_session):
    def _get_db():
        db = db_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_client(client, db_session):
    from app.database.seed import seed_database

    with db_session() as db:
        seed_database(db)
    return client
