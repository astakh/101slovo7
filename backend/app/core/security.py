"""
101slovo — Безопасность: JWT, bcrypt, хеширование refresh-токенов, cookie.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Response

from app.config import settings


# ─── Password hashing (bcrypt) ────────────────────────────────────────

def hash_password(password: str) -> str:
    """Хеширование пароля через bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля против хеша."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# ─── JWT tokens ───────────────────────────────────────────────────────

def create_access_token(user_id: int) -> str:
    """Создание JWT access-токена."""
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_TTL_MIN),
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """Декодирование и валидация access-токена."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


# ─── Refresh tokens ───────────────────────────────────────────────────

def generate_refresh_token() -> tuple[str, str, uuid.UUID]:
    """
    Генерация refresh-токена.
    Возвращает: (raw_token, token_hash, family_id)
    """
    raw_token = secrets.token_urlsafe(64)
    token_hash = hash_refresh_token(raw_token)
    family_id = uuid.uuid4()
    return raw_token, token_hash, family_id


def hash_refresh_token(token: str) -> str:
    """SHA-256 хеш refresh-токена для хранения в БД."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_refresh_token_hash(token: str, stored_hash: str) -> bool:
    """Проверка refresh-токена против сохранённого хеша (timing-safe)."""
    return secrets.compare_digest(hash_refresh_token(token), stored_hash)


# ─── Cookie helpers ───────────────────────────────────────────────────

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/auth/refresh"


def set_refresh_cookie(response: Response, raw_token: str) -> None:
    """Установка httpOnly cookie для refresh-токена."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=True,  # HTTPS only (в dev может потребоваться False)
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,  # Токен отправляется только на /auth/refresh
    )


def clear_refresh_cookie(response: Response) -> None:
    """Удаление refresh cookie."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
    )
