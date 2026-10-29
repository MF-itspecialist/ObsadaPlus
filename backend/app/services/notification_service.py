"""Powiadomienia e-mail dla sędziów.

* po publikacji obsady: sędzia dostaje swoje mecze; przy kolejnej wersji tylko ci, u których
  coś się zmieniło (termin, obiekt, skład, odwołanie, zdjęcie z meczu),
* przypomnienie o zgłoszeniu dyspozycyjności na najbliższy weekend (raz na weekend).

Wiadomości zawsze trafiają do ``outbox_messages``. Gdy w .env jest skrzynka (SMTP_HOST),
są od razu wysyłane w tle; bez niej czekają w skrzynce nadawczej (zakładka Powiadomienia)
i wyjdą po „Wyślij oczekujące”, gdy skrzynka zostanie skonfigurowana.
"""

from __future__ import annotations

import datetime as dt
import logging
import smtplib
import ssl
import threading
from collections.abc import Callable
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_config
from app.models import Availability, OutboxMessage, Publication, Referee
from app.services.export_service import ROLE_LABELS
from app.services.settings_service import get_settings

log = logging.getLogger(__name__)
DAYS = ["pon", "wt", "śr", "czw", "pt", "sob", "nd"]
_send_lock = threading.Lock()


# --- treść ---------------------------------------------------------------------
def _d(iso: str | dt.date) -> str:
    d = dt.date.fromisoformat(iso) if isinstance(iso, str) else iso
    return f"{DAYS[d.weekday()]} {d:%d.%m}"


def _period(date_from: dt.date, date_to: dt.date) -> str:
    return f"{date_from:%d.%m}–{date_to:%d.%m.%Y}"


def referee_rows(rows: list[dict[str, Any]], referee_id: int) -> list[dict[str, Any]]:
    """Mecze sędziego z wierszy publikacji, z jego rolą."""
    out = []
    for r in rows:
        mine = [c for c in r["crew"] if c["referee_id"] == referee_id]
        if mine:
            out.append({**r, "my_role": mine[0]["role"]})
    return out


def _signature(rows: list[dict[str, Any]]) -> list[tuple]:
    return [
        (r["match_id"], r["date"], r["start_time"], r["venue_name"], r["cancelled"], r["my_role"],
         tuple((c["role"], c["referee_id"]) for c in r["crew"]))
        for r in rows
    ]


def _match_block(r: dict[str, Any], referee_id: int) -> str:
    others = [
        f"{ROLE_LABELS.get(c['role'], c['role'])}: {c['referee_name']}"
        for c in r["crew"]
        if c["referee_id"] and c["referee_id"] != referee_id
    ]
    lines = [
        f"{_d(r['date'])} {r['start_time']}  {r['league']}".rstrip() + ("  — ODWOŁANY" if r["cancelled"] else ""),
        f"  {r['home_team']} – {r['away_team']}",
        f"  {r['venue_name']}" + (f", {r['venue_address']}" if r.get("venue_address") else ""),
        f"  Twoja rola: {ROLE_LABELS.get(r['my_role'], r['my_role'])}",
    ]
    if others:
        lines.append("  Zespół: " + "; ".join(others))
    return "\n".join(lines)


def _footer() -> str:
    url = get_config().app_url
    link = f"Szczegóły i zgłaszanie dyspozycyjności: {url}\n\n" if url else ""
    return f"\n{link}Wiadomość wysłana automatycznie z Obsada+. Odpowiedz obsadzającemu, jeśli coś się nie zgadza."


def publication_messages(
    db: Session, pub: Publication, previous: Publication | None
) -> tuple[list[OutboxMessage], list[str]]:
    """Wiadomości po publikacji. Zwraca też nazwiska sędziów, którzy powinni dostać mail, ale nie mają adresu."""
    ids = {c["referee_id"] for r in pub.rows for c in r["crew"] if c["referee_id"]}
    if previous is not None:
        ids |= {c["referee_id"] for r in previous.rows for c in r["crew"] if c["referee_id"]}
    period = _period(pub.date_from, pub.date_to)
    messages, without_email = [], []
    for ref in db.scalars(select(Referee).where(Referee.id.in_(ids))):
        now = referee_rows(pub.rows, ref.id)
        before = referee_rows(previous.rows, ref.id) if previous else []
        if previous is not None and _signature(now) == _signature(before):
            continue
        if not ref.notify_email:
            continue
        if not ref.email:
            without_email.append(ref.full_name)
            continue
        removed = [r for r in before if r["match_id"] not in {x["match_id"] for x in now}]
        if previous is None:
            subject = f"Obsada sędziowska {period}"
            intro = f"Twoja obsada na dni {period}:"
        else:
            subject = f"Zmiana obsady {period}"
            intro = f"Zmieniła się Twoja obsada na dni {period}. Aktualna lista:"
        parts = [f"Dzień dobry, {ref.first_name},", "", intro, ""]
        parts += [_match_block(r, ref.id) + "\n" for r in now] or ["(brak meczów)\n"]
        if removed:
            parts += ["Nie sędziujesz już:"]
            parts += [f"  {_d(r['date'])} {r['start_time']} {r['home_team']} – {r['away_team']}" for r in removed]
            parts.append("")
        messages.append(
            OutboxMessage(
                referee_id=ref.id, to_email=ref.email, to_name=ref.full_name, kind="publication",
                topic=f"publication:{pub.id}", subject=subject, body="\n".join(parts) + _footer(),
                status="pending", error="",
            )
        )
    return messages, sorted(without_email)


def notify_publication(db: Session, pub: Publication, previous: Publication | None) -> dict[str, Any]:
    if not get_settings(db).notify_on_publish:
        return {"queued": 0, "without_email": []}
    messages, without_email = publication_messages(db, pub, previous)
    db.add_all(messages)
    db.commit()
    return {"queued": len(messages), "without_email": without_email}


# --- przypomnienie o dyspozycyjności ------------------------------------------------
def upcoming_weekend(today: dt.date) -> list[dt.date]:
    """Najbliższe dni obsadowe pt–pon (od poniedziałku do czwartku: ten tydzień)."""
    friday = today + dt.timedelta(days=(4 - today.weekday()) % 7)
    return [friday + dt.timedelta(days=i) for i in range(4)]


def reminder_due(db: Session, now: dt.datetime) -> list[dt.date] | None:
    """Dni weekendu do przypomnienia, gdy pora (dzień i godzina z Ustawień, nadrabiane do czwartku)."""
    s = get_settings(db)
    wd = now.weekday()
    if not s.availability_reminder_enabled or not s.reminder_weekday <= wd <= 3:
        return None
    if wd == s.reminder_weekday and now.hour < s.reminder_hour:
        return None
    days = upcoming_weekend(now.date())
    topic = f"availability:{days[1].isoformat()}"
    if db.scalar(select(OutboxMessage.id).where(OutboxMessage.topic == topic).limit(1)) is not None:
        return None
    return days


def reminder_messages(db: Session, days: list[dt.date]) -> list[OutboxMessage]:
    declared = set(db.scalars(select(Availability.referee_id).where(Availability.date.in_(days))))
    topic = f"availability:{days[1].isoformat()}"
    period = _period(days[0], days[-1])
    url = get_config().app_url
    out = []
    for ref in db.scalars(select(Referee).where(Referee.active.is_(True), Referee.notify_email.is_(True), Referee.email != "")):
        if ref.id in declared:
            continue
        body = (
            f"Dzień dobry, {ref.first_name},\n\nnie mamy jeszcze Twojej dyspozycyjności na dni {period}.\n"
            + (f"Zgłoś ją w panelu sędziego: {url}\n" if url else "Zgłoś ją w panelu sędziego Obsada+.\n")
            + "\nBez zgłoszenia nie dostaniesz meczów w ten weekend."
        )
        out.append(
            OutboxMessage(
                referee_id=ref.id, to_email=ref.email, to_name=ref.full_name, kind="availability_reminder",
                topic=topic, subject=f"Dyspozycyjność na {period}", body=body + _footer(), status="pending", error="",
            )
        )
    if not out:
        # znacznik „przypomnienie zrobione” także wtedy, gdy wszyscy już zgłosili
        out.append(OutboxMessage(to_email="", to_name="", kind="availability_reminder", topic=topic,
                                 subject="(wszyscy zgłosili dyspozycyjność)", body="", status="sent", error=""))
    return out


def reminder_tick(session_factory: Callable[[], Session], now: dt.datetime) -> int:
    with session_factory() as db:
        days = reminder_due(db, now)
        if days is None:
            return 0
        msgs = reminder_messages(db, days)
        db.add_all(msgs)
        db.commit()
    send_pending(session_factory)
    return sum(1 for m in msgs if m.to_email)


# --- wysyłka -------------------------------------------------------------------
def smtp_configured() -> bool:
    return bool(get_config().smtp_host)


def _smtp_send(msg: OutboxMessage) -> None:
    cfg = get_config()
    em = EmailMessage()
    em["From"] = formataddr(("Obsada+", cfg.smtp_from or cfg.smtp_user))
    em["To"] = formataddr((msg.to_name, msg.to_email))
    em["Subject"] = msg.subject
    em.set_content(msg.body)
    context = ssl.create_default_context()
    if cfg.smtp_port == 465:
        with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, context=context, timeout=30) as s:
            if cfg.smtp_user:
                s.login(cfg.smtp_user, cfg.smtp_password)
            s.send_message(em)
    else:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30) as s:
            s.starttls(context=context)
            if cfg.smtp_user:
                s.login(cfg.smtp_user, cfg.smtp_password)
            s.send_message(em)


SENDER: Callable[[OutboxMessage], None] = _smtp_send


def send_pending(session_factory: Callable[[], Session], ids: list[int] | None = None) -> dict[str, int]:
    """Wysyła oczekujące (i wcześniej nieudane) wiadomości. Bez skrzynki nic nie robi."""
    if not smtp_configured():
        return {"sent": 0, "failed": 0}
    sent = failed = 0
    with _send_lock, session_factory() as db:
        q = select(OutboxMessage).where(OutboxMessage.status.in_(("pending", "failed")), OutboxMessage.to_email != "")
        if ids is not None:
            q = q.where(OutboxMessage.id.in_(ids))
        for msg in db.scalars(q.order_by(OutboxMessage.id)).all():
            try:
                SENDER(msg)
                msg.status, msg.error = "sent", ""
                msg.sent_at = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
                sent += 1
            except Exception as exc:  # noqa: BLE001 — błąd zapisujemy przy wiadomości
                msg.status, msg.error = "failed", str(exc)[:500]
                failed += 1
            db.commit()
    return {"sent": sent, "failed": failed}


def send_in_background(session_factory: Callable[[], Session]) -> None:
    if smtp_configured():
        threading.Thread(target=send_pending, args=(session_factory,), daemon=True).start()
