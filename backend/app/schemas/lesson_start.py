"""
101slovo — Pydantic-схемы для старта урока.
"""

from pydantic import BaseModel


class LessonStartRequest(BaseModel):
    """Запрос на старт урока."""
    word_ids: list[int]


class CurrentExerciseResponse(BaseModel):
    """Информация о текущем упражнении."""
    exercise_id: int
    order_index: int
    sentence: str


class LessonStartResponse(BaseModel):
    """Ответ после старта урока."""
    lesson_id: int
    lesson_number: int
    exercises_total: int
    created: bool
    current_exercise: CurrentExerciseResponse
