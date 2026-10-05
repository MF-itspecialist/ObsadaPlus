from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class SystemSetting(Base):
    """Ustawienie systemu (klucz → wartość JSON). Domyślne wartości są w settings_service."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
