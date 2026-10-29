import datetime as dt

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession, SessionToken
from app.config import get_config
from app.schemas.user import LoginRequest, PasswordChange, UserRead
from app.services import auth_service
from app.services.auth_service import AuthError

router = APIRouter(prefix="/api/auth", tags=["auth"])


def user_read(u) -> dict:
    return {
        "id": u.id,
        "login": u.login,
        "display_name": u.display_name,
        "role": u.role,
        "referee_id": u.referee_id,
        "referee_name": u.referee.full_name if u.referee else None,
        "active": u.active,
        "last_login_at": u.last_login_at.replace(tzinfo=dt.timezone.utc) if u.last_login_at else None,
    }


@router.post("/login", response_model=UserRead)
def login(data: LoginRequest, response: Response, db: DbSession):
    try:
        user, token = auth_service.login(db, data.login, data.password)
    except AuthError as exc:
        raise HTTPException(401, str(exc)) from exc
    cfg = get_config()
    response.set_cookie(
        auth_service.SESSION_COOKIE, token, max_age=cfg.session_days * 86400, httponly=True,
        samesite="lax", secure=cfg.cookie_secure, path="/",
    )
    return user_read(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, db: DbSession, token: SessionToken = None) -> None:
    auth_service.logout(db, token)
    response.delete_cookie(auth_service.SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser):
    return user_read(user)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: PasswordChange, user: CurrentUser, db: DbSession, token: SessionToken = None) -> None:
    """Zmiana własnego hasła. Wylogowuje pozostałe przeglądarki."""
    if not auth_service.verify_password(data.current_password, user.password_hash):
        raise HTTPException(422, "Obecne hasło jest nieprawidłowe")
    try:
        auth_service.set_password(db, user, data.new_password, keep_token=token)
    except AuthError as exc:
        raise HTTPException(422, str(exc)) from exc
