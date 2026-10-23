from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.referee import Referee


class User(Base):
    """Konto w aplikacji: obsadzający (ADMIN) albo sędzia (REFEREE, powiązany z rekordem sędziego)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(100), unique=True)
    display_name: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False, length=32))
    referee_id: Mapped[int | None] = mapped_column(ForeignKey("referees.id", ondelete="SET NULL"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    last_login_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    referee: Mapped[Referee | None] = relationship()
    sessions: Mapped[list[UserSession]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """Zalogowana przeglądarka. W ciasteczku jest losowy token, w bazie tylko jego skrót (SHA-256)."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    # UTC
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime)

    user: Mapped[User] = relationship(back_populates="sessions")
