import datetime as dt

from pydantic import BaseModel, Field

from app.models import UserRole


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class UserRead(BaseModel):
    id: int
    login: str
    display_name: str
    role: UserRole
    referee_id: int | None
    referee_name: str | None
    active: bool
    last_login_at: dt.datetime | None


class UserCreate(BaseModel):
    login: str = Field(min_length=1, max_length=100)
    display_name: str = Field(default="", max_length=200)
    role: UserRole
    referee_id: int | None = None
    # Puste = hasło wygeneruje serwer i zwróci je raz w odpowiedzi.
    password: str | None = Field(default=None, max_length=200)


class UserUpdate(BaseModel):
    display_name: str = Field(default="", max_length=200)
    role: UserRole
    referee_id: int | None = None
    active: bool = True


class UserWithPassword(BaseModel):
    user: UserRead
    # Hasło startowe / po resecie — pokazywane tylko raz.
    password: str | None


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)
