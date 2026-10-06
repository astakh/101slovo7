"""
101slovo — Пул подключений к PostgreSQL (psycopg 3, async).
Управление жизненным циклом через lifespan FastAPI.
"""
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from app.config import settings

# Глобальный пул соединений
pool: AsyncConnectionPool | None = None

async def init_pool() -> None:
    """
    Инициализация пула подключений.
    Вызывается в lifespan при старте приложения.
    """
    global pool
    pool = AsyncConnectionPool(
        conninfo=settings.DATABASE_URL,
        open=False,  # Откроем вручную в lifespan
        min_size=1,
        max_size=10,
        max_idle=300,  # Закрывать соединения, которые простаивают больше 5 минут
        reconnect_timeout=60,
        kwargs={
            "row_factory": dict_row,  # Строки как dict
            "autocommit": False,  # Транзакции управляем вручную
            # ─── TCP Keepalives ─────────────────────────────────────
            # Защита от "мертвых" TCP-соединений (частая проблема на Windows 
            # и при простое локального сервера). Заставляет ОС проверять связь.
            "keepalives": 1,
            "keepalives_idle": 30,      # Начинать проверку через 30 сек простоя
            "keepalives_interval": 10,  # Интервал между пингами 10 сек
            "keepalives_count": 5,      # Количество неудачных пингов до разрыва
        },
    )
    await pool.open()

async def close_pool() -> None:
    """
    Закрытие пула подключений.
    Вызывается в lifespan при остановке приложения.
    """
    global pool
    if pool:
        await pool.close()
        pool = None

def get_pool() -> AsyncConnectionPool:
    """Получить пул (для использования в зависимостях)."""
    if pool is None:
        raise RuntimeError("Connection pool is not initialized")
    return pool