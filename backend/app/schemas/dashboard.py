"""
101slovo — Pydantic-схемы для Dashboard.
"""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class DashboardDictionary(BaseModel):
    id: int
    name: str


class DashboardProfile(BaseModel):
    level: str
    dictionary: DashboardDictionary


class DashboardResume(BaseModel):
    lesson_id: int
    lesson_number: int
    exercises_done: int
    exercises_total: int


class DashboardWords(BaseModel):
    active: int = 0
    mastered: int = 0
    ignored: int = 0


class DashboardStreak(BaseModel):
    current: int
    longest: int
    today_done: bool


class DashboardResponse(BaseModel):
    profile: DashboardProfile
    today: date
    lessons_today: int
    daily_lesson_limit: int
    resets_at: datetime
    cta: Literal["start", "resume", "limit_reached"]
    resume: Optional[DashboardResume] = None
    words: DashboardWords
    streak: DashboardStreak
