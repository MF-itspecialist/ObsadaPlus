"""Harmonogram w tle: co minutę sprawdza zadania okresowe.

* codzienny import meczów (``auto_import_service``),
* przypomnienie o dyspozycyjności (``notification_service``).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.services import auto_import_service, notification_service

log = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, session_factory: Callable[[], Session], interval_s: float = 60.0) -> None:
        self.session_factory = session_factory
        self.interval_s = interval_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def tick(self) -> None:
        now = auto_import_service.now_local()
        for name, job in (
            ("import meczów", self._import),
            ("przypomnienie o dyspozycyjności", lambda: notification_service.reminder_tick(self.session_factory, now)),
        ):
            try:
                job()
            except Exception:  # noqa: BLE001 — jedno zadanie nie zatrzymuje pozostałych
                log.exception("Harmonogram: %s — błąd", name)

    def _import(self) -> None:
        with self.session_factory() as db:
            due = auto_import_service.auto_run_due(db, auto_import_service.now_local())
        if due:
            auto_import_service.run_import(self.session_factory, "auto")

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_s):
            self.tick()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
