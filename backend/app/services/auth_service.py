"""Konta i logowanie: hasła (scrypt), sesje w ciasteczku, ochrona przed zgadywaniem haseł."""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import secrets
import threading
import time

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_config
from app.models import Referee, User, UserRole, UserSession

SESSION_COOKIE = "obsada_session"
MIN_PASSWORD_LENGTH = 8
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


class AuthError(Exception):
    pass


# --- hasła ------------------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_SCRYPT)
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), dklen=32, n=int(n), r=int(r), p=int(p))
    return hmac.compare_digest(actual.hex(), digest)


_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def generate_password() -> str:
    """Hasło startowe do przekazania sędziemu: 12 znaków bez mylących (0/O, 1/l)."""
    alphabet = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(12))


def check_password_strength(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Hasło musi mieć co najmniej {MIN_PASSWORD_LENGTH} znaków")


# --- blokada po nieudanych próbach -------------------------------------------------
class LoginThrottle:
    """Po 5 błędnych hasłach dla loginu blokada na 5 minut (w pamięci procesu)."""

    def __init__(self, limit: int = 5, window_s: float = 300) -> None:
        self.limit, self.window_s = limit, window_s
        self._fails: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        return [t for t in self._fails.get(key, []) if now - t < self.window_s]

    def blocked_for(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            recent = self._recent(key, now)
            self._fails[key] = recent
            if len(recent) < self.limit:
                return 0
            return int(self.window_s - (now - recent[0])) + 1

    def fail(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._fails[key] = self._recent(key, now) + [now]

    def reset(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)


throttle = LoginThrottle()


# --- sesje ------------------------------------------------------------------------
def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None, microsecond=0)


def normalize_login(login: str) -> str:
    return login.strip().lower()


def login(db: Session, login_: str, password: str) -> tuple[User, str]:
    """Sprawdza hasło i tworzy sesję. Zwraca (użytkownik, token do ciasteczka)."""
    key = normalize_login(login_)
    wait = throttle.blocked_for(key)
    if wait:
        raise AuthError(f"Za dużo nieudanych prób. Spróbuj ponownie za {max(1, wait // 60)} min.")
    user = db.scalar(select(User).where(User.login == key))
    # Dla nieistniejącego loginu też liczymy skrót — czas odpowiedzi nie zdradza, które loginy istnieją.
    stored = user.password_hash if user else _DUMMY_HASH
    if not verify_password(password, stored) or user is None or not user.active:
        throttle.fail(key)
        raise AuthError("Nieprawidłowy login lub hasło")
    throttle.reset(key)
    token = secrets.token_urlsafe(32)
    now = _utcnow()
    db.add(UserSession(token_hash=_token_hash(token), user_id=user.id, expires_at=now + dt.timedelta(days=get_config().session_days)))
    user.last_login_at = now
    db.execute(delete(UserSession).where(UserSession.expires_at < now))
    db.commit()
    return user, token


def user_for_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    session = db.scalar(
        select(UserSession)
        .options(selectinload(UserSession.user).selectinload(User.referee))
        .where(UserSession.token_hash == _token_hash(token))
    )
    if session is None or session.expires_at < _utcnow() or not session.user.active:
        return None
    return session.user


def logout(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(UserSession).where(UserSession.token_hash == _token_hash(token)))
        db.commit()


def revoke_sessions(db: Session, user: User, keep_token: str | None = None) -> None:
    q = delete(UserSession).where(UserSession.user_id == user.id)
    if keep_token:
        q = q.where(UserSession.token_hash != _token_hash(keep_token))
    db.execute(q)


# --- konta ------------------------------------------------------------------------
def _validate(db: Session, role: UserRole, referee_id: int | None, user_id: int | None = None) -> None:
    if role == UserRole.REFEREE:
        if referee_id is None:
            raise AuthError("Konto sędziego musi być powiązane z sędzią z listy")
        if db.get(Referee, referee_id) is None:
            raise AuthError(f"Sędzia {referee_id} nie istnieje")
        taken = db.scalar(select(User).where(User.referee_id == referee_id, User.id != (user_id or 0)))
        if taken:
            raise AuthError(f"Ten sędzia ma już konto: {taken.login}")


def create_user(
    db: Session, login_: str, password: str, role: UserRole, display_name: str = "", referee_id: int | None = None
) -> User:
    key = normalize_login(login_)
    if not key:
        raise AuthError("Login nie może być pusty")
    if db.scalar(select(User).where(User.login == key)):
        raise AuthError(f"Login {key} jest już zajęty")
    check_password_strength(password)
    referee_id = referee_id if role == UserRole.REFEREE else None
    _validate(db, role, referee_id)
    if not display_name and referee_id:
        display_name = db.get(Referee, referee_id).full_name
    user = User(login=key, display_name=display_name or key, password_hash=hash_password(password), role=role,
                referee_id=referee_id, active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session, user: User, *, display_name: str, role: UserRole, referee_id: int | None, active: bool, acting: User
) -> User:
    referee_id = referee_id if role == UserRole.REFEREE else None
    _validate(db, role, referee_id, user.id)
    if user.id == acting.id and (role != UserRole.ADMIN or not active):
        raise AuthError("Nie możesz odebrać sobie uprawnień obsadzającego ani wyłączyć własnego konta")
    user.display_name, user.role, user.referee_id, user.active = display_name or user.login, role, referee_id, active
    if not active:
        revoke_sessions(db, user)
    db.commit()
    db.refresh(user)
    return user


def set_password(db: Session, user: User, password: str, keep_token: str | None = None) -> None:
    check_password_strength(password)
    user.password_hash = hash_password(password)
    revoke_sessions(db, user, keep_token)
    db.commit()


def delete_user(db: Session, user: User, acting: User) -> None:
    if user.id == acting.id:
        raise AuthError("Nie możesz usunąć własnego konta")
    db.delete(user)
    db.commit()


def ensure_admin(db: Session) -> User | None:
    """Tworzy pierwsze konto obsadzającego z ADMIN_LOGIN / ADMIN_PASSWORD, gdy w bazie nie ma kont."""
    cfg = get_config()
    if not cfg.admin_password or db.scalar(select(func.count()).select_from(User)):
        return None
    return create_user(db, cfg.admin_login, cfg.admin_password, UserRole.ADMIN, "Obsadzający")
