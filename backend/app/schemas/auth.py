"""
101slovo — Pydantic-схемы для аутентификации.
"""

from pydantic import BaseModel, EmailStr, Field


class AuthRequest(BaseModel):
    """Схема для регистрации и входа."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class TokenResponse(BaseModel):
    """Ответ с access-токеном."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Информация о пользователе."""
    id: int
    email: str
    is_onboarded: bool
    is_admin: bool
    timezone: str | None = None
