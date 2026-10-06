"""
101slovo — Pydantic-схемы для профиля и статистики.
"""

from datetime import date

from pydantic import BaseModel


class HeatmapEntry(BaseModel):
    date: date
    count: int


class ProfileStatsResponse(BaseModel):
    streak_current: int
    streak_longest: int
    heatmap: list[HeatmapEntry]
    accuracy_30_days: float
    accuracy_all_time: float
    words_active: int
    words_mastered: int
    words_ignored: int
    completed_lessons: int
