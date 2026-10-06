"""
101slovo — Pydantic-схемы для онбординга.
"""
from typing import Literal
from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    """Схема для завершения онбординга."""
    timezone: str
    level: Literal["A1", "A2", "B1", "B2", "C1", "C2"]
    dictionary_id: int
    # ge=1 оставляем (нижняя граница фиксирована)
    # le убираем — верхняя граница проверяется в роутере через settings
    words_per_lesson: int = Field(default=5, ge=1, description="Количество слов в одном уроке")
    daily_lesson_limit: int = Field(default=1, ge=1, description="Дневной лимит уроков")


class OnboardingResponse(BaseModel):
    """Ответ после завершения онбординга."""
    status: str = "ok"


class DictionaryResponse(BaseModel):
    """Схема словаря."""
    id: int
    code: str
    name: str
    description: str | None = None


class OnboardingLimitsResponse(BaseModel):
    """Лимиты для онбординга (читаются из .env на бэкенде)."""
    words_per_lesson_min: int
    words_per_lesson_max: int
    daily_lesson_limit_max: int