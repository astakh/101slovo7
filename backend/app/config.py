"""
101slovo — Конфигурация приложения
Загрузка переменных окружения через pydantic-settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    # ─── Database ────────────────────────────────────────────────────
    DATABASE_URL: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """
        Нормализует DATABASE_URL для psycopg 3.
        
        Преобразует:
        - postgresql+asyncpg://... -> postgresql://...
        - postgresql+psycopg://... -> postgresql://...
        - postgres://... -> postgresql://...
        """
        if not isinstance(v, str):
            return v
        
        # Убираем диалект (+asyncpg, +psycopg и т.д.)
        for dialect in ("+asyncpg", "+psycopg", "+pg8000", "+aiopg"):
            v = v.replace(dialect, "")
        
        # postgres:// -> postgresql://
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql://", 1)
        
        return v

    # ─── JWT & Auth ──────────────────────────────────────────────────
    JWT_SECRET: str
    ACCESS_TOKEN_TTL_MIN: int = 30
    REFRESH_TOKEN_TTL_DAYS: int = 30

    # ─── App Limits & Defaults ───────────────────────────────────────
    DEFAULT_DICTIONARY_CODE: str = "general"
    WORDS_PER_LESSON_DEFAULT: int = 5
    WORDS_PER_LESSON_MIN: int = 1
    WORDS_PER_LESSON_MAX: int = 10
    DAILY_LESSON_LIMIT_DEFAULT: int = 1
    DAILY_LESSON_LIMIT_MAX: int = Field(default=5, alias="DAILY_LESSON_MAX")

    # ─── GigaChat LLM ────────────────────────────────────────────────
    GIGACHAT_AUTH_KEY: str
    GIGACHAT_SCOPE: str
    GIGACHAT_MODEL: str
    GIGACHAT_MAX_CONCURRENCY: int = 5
    GIGACHAT_TOKEN_REFRESH_MINUTES: int = 10
    GIGACHAT_VERIFY_SSL: bool = True  # Отключите для разработки (False)

    # ─── LLM Generation Params ───────────────────────────────────────
    GEN_TEMPERATURE: float = 0.7
    EVAL_TEMPERATURE: float = 0.2
    LLM_LOG_RETENTION_DAYS: int = 90

    # ─── CORS ────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(default_factory=list)

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "case_sensitive": True,
    }


settings = Settings()
