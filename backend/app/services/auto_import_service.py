"""Automatyczna aktualizacja meczów: codzienny import z 90minut.pl.

Harmonogram to wątek w backendzie: co minutę sprawdza, czy dziś (czas polski) po godzinie
z Ustawień był już import automatyczny; jeśli nie — uruchamia go. Restart aplikacji po tej
godzinie nadrabia import tego samego dnia. Każde uruchomienie (też ręczne) zapisuje się
w ``import_runs`` razem z listą obsadzonych meczów, którym zmienił się termin lub obiekt.
Juniorzy z Łączy Nas Piłka zostają importowani ręcznie (reCAPTCHA).
"""

from __future__ import annotations

import datetime as dt
import logging
import threading
from collections.abc import Callable
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importers.import_service import import_matches
from app.importers.m90_importer import M90MatchImporter
from app.models import ImportRun
from app.services.geocoding_service import get_geocoder
from app.services.mileage_service import season_bounds
from app.services.settings_service import get_settings

log = logging.getLogger(__name__)
WARSAW = ZoneInfo("Europe/Warsaw")
SOURCE = "90minut.pl"

_lock = threading.Lock()


def now_local() -> dt.datetime:
    return dt.datetime.now(WARSAW)


class UpcomingM90Importer(M90MatchImporter):
    """Tylko mecze od dziś — rozegranych nie ruszamy."""

    def __init__(self, *args, today: dt.date, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.today = today

    def fetch_matches(self):
        records = super().fetch_matches()
        upcoming = [r for r in records if r.date >= self.today]
        if len(upcoming) < len(records):
            self.warnings.append(f"Pominięto {len(records) - len(upcoming)} meczów rozegranych przed {self.today:%d.%m.%Y}")
        return upcoming


def default_importer(db: Session, today: dt.date) -> M90MatchImporter:
    s = get_settings(db)
    start_year = season_bounds(today)[0].year
    return UpcomingM90Importer(s.m90_season_id, s.m90_region_id, start_year, today=today)


def is_running() -> bool:
    return _lock.locked()


def run_import(
    session_factory: Callable[[], Session],
    trigger: str,
    importer_factory: Callable[[Session, dt.date], object] | None = None,
    run_id: int | None = None,
) -> int | None:
    """Jeden import. Zwraca id zapisu w ``import_runs``; ``None``, gdy inny import właśnie trwa."""
    if not _lock.acquire(blocking=False):
        return None
    try:
        with session_factory() as db:
            run = db.get(ImportRun, run_id) if run_id else None
            if run is None:
                run = ImportRun(source=SOURCE, trigger=trigger, status="running", changes=[], messages=[])
                db.add(run)
                db.commit()
            try:
                importer = (importer_factory or default_importer)(db, now_local().date())
                result = import_matches(db, importer, get_settings(db).default_match_duration_minutes, get_geocoder())
                run.created, run.updated = result["created"], result["updated"]
                run.changes, run.messages = result["changes"], result["errors"]
                run.status = "ok"
            except Exception as exc:  # noqa: BLE001 — błąd zapisujemy w historii, harmonogram działa dalej
                db.rollback()
                log.exception("Import meczów nie powiódł się")
                run.status = "error"
                run.messages = [f"Import nie powiódł się: {exc}"]
            run.finished_at = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
            db.commit()
            return run.id
    finally:
        _lock.release()


def start_background(session_factory: Callable[[], Session], trigger: str = "manual") -> int | None:
    """Ręczne „Uruchom teraz”: zapis w historii od razu, import w tle. ``None`` = już trwa."""
    if is_running():
        return None
    with session_factory() as db:
        run = ImportRun(source=SOURCE, trigger=trigger, status="running", changes=[], messages=[])
        db.add(run)
        db.commit()
        run_id = run.id
    threading.Thread(target=run_import, args=(session_factory, trigger), kwargs={"run_id": run_id}, daemon=True).start()
    return run_id


def auto_run_due(db: Session, now: dt.datetime) -> bool:
    """Czy pora na import automatyczny: włączony, po godzinie z Ustawień i jeszcze nie dziś."""
    s = get_settings(db)
    if not s.auto_import_enabled or now.hour < s.auto_import_hour:
        return False
    day_start = dt.datetime.combine(now.date(), dt.time(), WARSAW).astimezone(dt.timezone.utc).replace(tzinfo=None)
    done = db.scalar(
        select(ImportRun.id).where(ImportRun.trigger == "auto", ImportRun.started_at >= day_start).limit(1)
    )
    return done is None
