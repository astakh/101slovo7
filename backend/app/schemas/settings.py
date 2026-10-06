"""
101slovo — Pydantic-схемы для настроек.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class LearningProfileResponse(BaseModel):
    level: str
    dictionary: dict
    daily_lesson_limit: int
    daily_lesson_limit_max: int
    words_per_lesson: int
    words_per_lesson_min: int
    words_per_lesson_max: int
    stats: dict


class LearningProfileUpdate(BaseModel):
    level: Optional[Literal["A1", "A2", "B1", "B2"]] = None
    dictionary_id: Optional[int] = None
    daily_lesson_limit: Optional[int] = Field(None, ge=1)
    words_per_lesson: Optional[int] = Field(None, ge=1)


class TimezoneUpdate(BaseModel):
    timezone: str


class TimezoneResponse(BaseModel):
    today: str
    lessons_today: int
    resets_at: str
    streak: dict
