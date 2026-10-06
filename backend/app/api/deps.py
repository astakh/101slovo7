"""
101slovo — Зависимости FastAPI (Depends).
"""

from typing import AsyncGenerator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import AsyncConnection

from app.config import settings
from app.db.pool import get_pool


# ─── Database dependency ──────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncConnection, None]:
    """
    Зависимость для получения асинхронного соединения с БД.

    Использование:
        @router.get("/")
        async def endpoint(db: AsyncConnection = Depends(get_db)):
            ...

    Соединение автоматически возвращается в пул после выхода из контекста.
    """
    pool = get_pool()
    async with pool.connection() as conn:
        yield conn


# ─── Auth dependency ──────────────────────────────────────────────────

security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """
    Зависимость для извлечения user_id из access-токена.

    Использование:
        @router.get("/me")
        async def me(user_id: int = Depends(get_current_user_id)):
            ...
    """
    import logging
    logger = logging.getLogger(__name__)
    
    token_preview = credentials.credentials[:20] + "..." if len(credentials.credentials) > 20 else credentials.credentials
    logger.info(f"🔍 Получен токен: {token_preview}")
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        logger.info(f"✅ Токен декодирован успешно: {payload}")
        
        if payload.get("type") != "access":
            logger.error(f"❌ Неверный тип токена: {payload.get('type')}")
            raise ValueError("Invalid token type")
        
        user_id = int(payload["sub"])
        logger.info(f"✅ User ID извлечён: {user_id}")
        return user_id
    except jwt.ExpiredSignatureError as e:
        logger.error(f"❌ Токен истёк: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"❌ Невалидный токен: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (ValueError, KeyError) as e:
        logger.error(f"❌ Ошибка извлечения user_id: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_admin_user_id(
    user_id: int = Depends(get_current_user_id),
    db: AsyncConnection = Depends(get_db),
) -> int:
    """
    Зависимость для проверки прав администратора.
    
    Проверяет, что пользователь является администратором.
    Использование:
        @router.get("/admin/...")
        async def admin_endpoint(admin_id: int = Depends(get_current_admin_user_id)):
            ...
    """
    cur = await db.execute("SELECT is_admin FROM users WHERE id = %s", [user_id])
    user = await cur.fetchone()
    if not user or not user["is_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin_required",
        )
    return user_id
