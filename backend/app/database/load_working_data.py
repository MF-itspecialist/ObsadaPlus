"""Dane robocze: lista sędziów do testów na realistycznej skali.

Nazwiska i imiona są fikcyjne; z listy KS Warszawa zachowano tylko liczebność
i licencje (miejsce zamieszkania wylosowane z dzielnic Warszawy i okolicznych miast).

    python -m app.database.load_working_data            # dopisz brakujących sędziów
    python -m app.database.load_working_data --replace  # usuń obecnych sędziów i wczytaj listę
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Referee

REFEREES_FILE = Path(__file__).parent / "working_data" / "referees.json"


def load_referees(db: Session, path: Path = REFEREES_FILE, replace: bool = False) -> int:
    """Wczytuje sędziów z pliku JSON. Zwraca liczbę dodanych."""
    records = json.loads(path.read_text(encoding="utf-8"))
    if replace:
        for ref in db.scalars(select(Referee)):
            db.delete(ref)  # kaskadowo: dyspozycyjność i przypisania
        db.flush()
    existing = {(r.first_name, r.last_name) for r in db.scalars(select(Referee))}
    added = 0
    for rec in records:
        if (rec["first_name"], rec["last_name"]) in existing:
            continue
        db.add(Referee(address=rec.get("address", ""), notes="Dane robocze (fikcyjne)", **{k: v for k, v in rec.items() if k != "address"}))
        added += 1
    db.commit()
    return added


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--replace", action="store_true", help="usuń obecnych sędziów przed wczytaniem")
    args = parser.parse_args()

    from app.database.db import SessionLocal

    with SessionLocal() as session:
        print(f"Dodano sędziów: {load_referees(session, replace=args.replace)}")
