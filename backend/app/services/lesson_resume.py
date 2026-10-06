"""
101slovo — Сервис возобновления урока.
Возвращает текущее упражнение для продолжения урока.
"""

from psycopg import AsyncConnection


async def get_current_exercise(
    db: AsyncConnection, *, profile_id: int, lesson_id: int
) -> dict:
    """
    GET /lesson/{id}/current — возврат текущего упражнения для возобновления.
    
    Возвращает:
    - lesson_id
    - exercises_done / exercises_total
    - current_exercise (первое невыполненное)
    """
    # Проверяем урок
    cur = await db.execute(
        """SELECT l.id, l.status FROM lessons l 
           WHERE l.id = %s AND l.learning_profile_id = %s""",
        [lesson_id, profile_id],
    )
    lesson = await cur.fetchone()
    if not lesson:
        raise ValueError("lesson_not_found")

    if lesson["status"] != "in_progress":
        raise ValueError("lesson_not_active")

    # Считаем прогресс
    cur = await db.execute(
        """SELECT COUNT(*) as total,
                  COUNT(*) FILTER (WHERE status = 'evaluated') as done
           FROM lesson_exercises WHERE lesson_id = %s""",
        [lesson_id],
    )
    stats = await cur.fetchone()

    # Получаем первое невыполненное упражнение
    cur = await db.execute(
        """SELECT id, order_index, target_sentence, reference_translation, target_words
           FROM lesson_exercises 
           WHERE lesson_id = %s AND status = 'pending' 
           ORDER BY order_index LIMIT 1""",
        [lesson_id],
    )
    current = await cur.fetchone()

    if not current:
        # Все упражнения оценены, но урок не завершён — не должно происходить
        raise ValueError("lesson_not_active")

    return {
        "lesson_id": lesson_id,
        "exercises_done": stats["done"],
        "exercises_total": stats["total"],
        "current_exercise": {
            "exercise_id": current["id"],
            "order_index": current["order_index"],
            "sentence": current["target_sentence"],
            "reference_translation": current["reference_translation"],
            "target_words": current["target_words"],
        },
    }
