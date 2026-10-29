from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.auth import user_read
from app.api.deps import AdminUser, DbSession, not_found
from app.models import User
from app.schemas.user import UserCreate, UserRead, UserUpdate, UserWithPassword
from app.services import auth_service
from app.services.auth_service import AuthError

router = APIRouter(prefix="/api/users", tags=["users"])


def _get(db, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise not_found("Użytkownik", user_id)
    return user


@router.get("", response_model=list[UserRead])
def list_users(db: DbSession):
    users = db.scalars(select(User).options(selectinload(User.referee)).order_by(User.role, User.login))
    return [user_read(u) for u in users]


@router.post("", response_model=UserWithPassword, status_code=status.HTTP_201_CREATED)
def create(data: UserCreate, db: DbSession):
    password = data.password or auth_service.generate_password()
    try:
        user = auth_service.create_user(db, data.login, password, data.role, data.display_name, data.referee_id)
    except AuthError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"user": user_read(user), "password": None if data.password else password}


@router.put("/{user_id}", response_model=UserRead)
def update(user_id: int, data: UserUpdate, db: DbSession, acting: AdminUser):
    try:
        user = auth_service.update_user(
            db, _get(db, user_id), display_name=data.display_name, role=data.role, referee_id=data.referee_id,
            active=data.active, acting=acting,
        )
    except AuthError as exc:
        raise HTTPException(422, str(exc)) from exc
    return user_read(user)


@router.post("/{user_id}/reset-password", response_model=UserWithPassword)
def reset_password(user_id: int, db: DbSession):
    """Nowe losowe hasło (pokazywane raz); wylogowuje wszystkie sesje tego konta."""
    user = _get(db, user_id)
    password = auth_service.generate_password()
    auth_service.set_password(db, user, password)
    return {"user": user_read(user), "password": password}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(user_id: int, db: DbSession, acting: AdminUser) -> None:
    try:
        auth_service.delete_user(db, _get(db, user_id), acting)
    except AuthError as exc:
        raise HTTPException(422, str(exc)) from exc
