"""Inicjalizacja bazy: migracje Alembic (+ opcjonalnie dane testowe).

Uruchomienie z linii poleceń:
    python -m app.database.init_db            # migracje
    python -m app.database.init_db --seed     # migracje + dane testowe (gdy baza pusta)
    python -m app.database.init_db --reset    # usuń wszystko, migracje, dane testowe
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import get_config
from app.database.db import Base, SessionLocal, engine

log = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parents[2]


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", get_config().database_url)
    return cfg


def migrate() -> None:
    command.upgrade(alembic_config(), "head")


def reset() -> None:
    import app.models  # noqa: F401  rejestracja tabel

    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")


def init_db(seed: bool = False) -> None:
    migrate()
    if seed:
        from app.database.seed import seed_database

        with SessionLocal() as db:
            if seed_database(db):
                log.info("Wczytano dane testowe")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Inicjalizacja bazy Obsada+")
    parser.add_argument("--seed", action="store_true", help="wczytaj dane testowe, jeśli baza jest pusta")
    parser.add_argument("--reset", action="store_true", help="usuń dane i utwórz bazę od nowa (z danymi testowymi)")
    args = parser.parse_args()
    if args.reset:
        reset()
    init_db(seed=args.seed or args.reset)
    print("Baza gotowa.")
