"""
101slovo — Роутер аутентификации.
Регистрация, вход, ротация refresh-токенов, выход.
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from psycopg import AsyncConnection

from app.api.deps import get_current_user_id, get_db
from app.core.rate_limit import limiter
from app.core.security import (
    clear_refresh_cookie,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    hash_password,
    set_refresh_cookie,
    verify_password,
)
from app.schemas.auth import AuthRequest, TokenResponse, UserResponse

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(
    req: AuthRequest,
    request: Request,
    response: Response,
    db: AsyncConnection = Depends(get_db),
):
    """
    Регистрация нового пользователя.
    
    - Создаёт пользователя с хешированным паролем
    - Генерирует access и refresh токены
    - Refresh токен сохраняется в БД как SHA-256 хеш
    - Логирует событие signup
    """
    limiter.check_ip_limit(request.client.host)
    email = req.email.strip().lower()

    async with db.transaction():
        # Проверка занятости email
        cur = await db.execute("SELECT id FROM users WHERE email = %s", [email])
        if await cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="email_taken",
            )

        # Создание пользователя
        pwd_hash = hash_password(req.password)
        cur = await db.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
            [email, pwd_hash],
        )
        user_id = (await cur.fetchone())["id"]

        # Генерация и сохранение refresh токена
        raw_token, token_hash, family_id = generate_refresh_token()
        await db.execute(
            """INSERT INTO refresh_tokens (user_id, family_id, token_hash, expires_at) 
               VALUES (%s, %s, %s, now() + interval '30 days')""",
            [user_id, family_id, token_hash],
        )

        # Логирование события
        await db.execute(
            "INSERT INTO events (user_id, type, payload) VALUES (%s, %s, %s)",
            [user_id, "signup", json.dumps({"email": email})],
        )

    access_token = create_access_token(user_id)
    set_refresh_cookie(response, raw_token)

    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    req: AuthRequest,
    request: Request,
    response: Response,
    db: AsyncConnection = Depends(get_db),
):
    """
    Вход пользователя.
    
    - Проверяет email и пароль
    - При неудаче записывает попытку в rate limiter
    - При успехе генерирует токены
    """
    limiter.check_ip_limit(request.client.host)
    email = req.email.strip().lower()

    # Проверка лимита неудачных попыток
    limiter.check_email_limit(email)

    async with db.transaction():
        cur = await db.execute(
            "SELECT id, password_hash FROM users WHERE email = %s",
            [email],
        )
        user = await cur.fetchone()

        if not user or not verify_password(req.password, user["password_hash"]):
            limiter.record_failure(email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_credentials",
            )

        # Генерация токенов
        raw_token, token_hash, family_id = generate_refresh_token()
        await db.execute(
            """INSERT INTO refresh_tokens (user_id, family_id, token_hash, expires_at) 
               VALUES (%s, %s, %s, now() + interval '30 days')""",
            [user["id"], family_id, token_hash],
        )

    access_token = create_access_token(user["id"])
    set_refresh_cookie(response, raw_token)

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncConnection = Depends(get_db),
):
    """
    Обновление access-токена через refresh-токен из cookie.
    
    - Ротация refresh-токенов (новый токен при каждом обновлении)
    - Защита от кражи: если использован отозванный токен, отзываем всё семейство
    - family_id связывает все токены в цепочке
    """
    raw_token = request.cookies.get("refresh_token")
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )

    token_hash = hash_refresh_token(raw_token)

    async with db.transaction():
        # Поиск токена в БД
        cur = await db.execute(
            """SELECT id, user_id, family_id, revoked_at, expires_at 
               FROM refresh_tokens WHERE token_hash = %s""",
            [token_hash],
        )
        old_token = await cur.fetchone()

        if not old_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_credentials",
            )

        # Проверка срока действия
        if old_token["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token_expired",
            )

        # Защита от кражи: если токен уже отозван, отзываем всё семейство
        if old_token["revoked_at"] is not None:
            await db.execute(
                "UPDATE refresh_tokens SET revoked_at = now() WHERE family_id = %s AND revoked_at IS NULL",
                [old_token["family_id"]],
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token_reused",
            )

        # Ротация: создаём новый токен
        new_raw, new_hash, _ = generate_refresh_token()
        cur_new = await db.execute(
            """INSERT INTO refresh_tokens (user_id, family_id, token_hash, expires_at) 
               VALUES (%s, %s, %s, now() + interval '30 days') RETURNING id""",
            [old_token["user_id"], old_token["family_id"], new_hash],
        )
        new_token_id = (await cur_new.fetchone())["id"]

        # Помечаем старый как использованный
        await db.execute(
            "UPDATE refresh_tokens SET revoked_at = now(), replaced_by = %s WHERE id = %s",
            [new_token_id, old_token["id"]],
        )

    access_token = create_access_token(old_token["user_id"])
    set_refresh_cookie(response, new_raw)

    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncConnection = Depends(get_db),
):
    """
    Выход пользователя.
    
    - Отзывает текущий refresh-токен
    - Удаляет cookie
    """
    raw_token = request.cookies.get("refresh_token")
    if raw_token:
        token_hash = hash_refresh_token(raw_token)
        await db.execute(
            "UPDATE refresh_tokens SET revoked_at = now() WHERE token_hash = %s AND revoked_at IS NULL",
            [token_hash],
        )

    clear_refresh_cookie(response)
    return {"status": "ok"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: int = Depends(get_current_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Получение информации о текущем пользователе.
    """
    cur = await db.execute(
        "SELECT id, email, is_onboarded, is_admin, timezone FROM users WHERE id = %s",
        [user_id],
    )
    user = await cur.fetchone()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user_not_found",
        )
    return UserResponse(**user)
