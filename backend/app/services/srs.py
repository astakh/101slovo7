"""
101slovo — Алгоритм интервального повторения (SRS).
Чистая функция без обращения к БД, строго по п. 5.1 ТЗ.
"""

# Интервалы повторения по стадиям (в уроках)
INTERVALS = [1, 2, 3, 7, 11, 30]
MAX_STAGE = 6


def srs_update(stage: int, result: str, lesson_number: int) -> tuple[int, int | None, str]:
    """
    Алгоритм 5.1: Обновление SRS.
    
    Args:
        stage: Текущая стадия слова (0-6)
        result: Результат оценки ('correct', 'typo', 'incorrect')
        lesson_number: Номер текущего урока
    
    Returns:
        Кортеж (new_stage, due_lesson_number, status)
    
    Тестовые случаи для урока №10:
        stage=0, correct   -> (1, 11, active)
        stage=0, typo      -> (1, 11, active)
        stage=0, incorrect -> (0, 11, active)
        stage=6, correct   -> (6, None, mastered)
        stage=6, incorrect -> (5, 21, active)
        stage=3, incorrect -> (2, 12, active)
    """
    success = result in ("correct", "typo")

    if success:
        if stage == MAX_STAGE:
            return (MAX_STAGE, None, "mastered")
        new_stage = stage + 1
    else:
        new_stage = max(stage - 1, 0)

    interval = INTERVALS[max(new_stage - 1, 0)]
    due = lesson_number + interval

    return (new_stage, due, "active")
