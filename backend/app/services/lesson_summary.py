"""
101slovo — Сервис итогов урока.
Алгоритм 5.6 из ТЗ: расчёт метрик урока и стрика.
"""

from psycopg import AsyncConnection

from app.utils.datetime import calculate_streak, get_user_today


async def get_lesson_summary(
    db: AsyncConnection, *, user_id: int, profile_id: int, lesson_id: int
) -> dict:
    """
    Алгоритм 5.6: Итоги урока.
    
    Возвращает:
    - Метрики урока (слова, правильные/неправильные, новые)
    - Стрик с extended_today
    - Количество добавленных подсказок
    """
    # 1. Проверяем владение и статус урока
    cur = await db.execute(
        """SELECT l.id, l.lesson_number, l.status, l.completed_local_date, l.completed_at
           FROM lessons l WHERE l.id = %s AND l.learning_profile_id = %s""",
        [lesson_id, profile_id],
    )
    lesson = await cur.fetchone()
    if not lesson:
        raise ValueError("lesson_not_found")

    if lesson["status"] != "completed":
        raise ValueError("lesson_not_completed")

    # 2. Собираем метрики из упражнений
    cur = await db.execute(
        "SELECT target_words, suggested_words FROM lesson_exercises WHERE lesson_id = %s",
        [lesson_id],
    )
    exercises = await cur.fetchall()

    words_total = 0
    new_words = 0
    correct = 0
    typo = 0
    incorrect = 0

    for ex in exercises:
        for tw in ex["target_words"]:
            words_total += 1
            if tw.get("is_new", False):
                new_words += 1

            result = tw.get("result")
            if result == "correct":
                correct += 1
            elif result == "typo":
                typo += 1
            elif result == "incorrect":
                incorrect += 1

    # Вычисляем точность
    without_errors = correct + typo
    accuracy = (without_errors / words_total * 100) if words_total > 0 else 0
    
    # Вычисляем время урока
    cur = await db.execute(
        """SELECT started_at, completed_at 
           FROM lessons WHERE id = %s""",
        [lesson_id],
    )
    lesson_times = await cur.fetchone()
    time_spent = 0
    if lesson_times and lesson_times["started_at"] and lesson_times["completed_at"]:
        time_spent = int((lesson_times["completed_at"] - lesson_times["started_at"]).total_seconds())

    # 3. Расчёт стрика
    cur = await db.execute(
        """SELECT timezone FROM users u 
           JOIN learning_profiles lp ON lp.user_id = u.id 
           WHERE lp.id = %s""",
        [profile_id],
    )
    user_tz = (await cur.fetchone())["timezone"]
    today = get_user_today(user_tz)

    cur = await db.execute(
        """SELECT DISTINCT completed_local_date FROM lessons 
           WHERE learning_profile_id = %s AND status = 'completed' 
             AND completed_local_date IS NOT NULL""",
        [profile_id],
    )
    dates = {r["completed_local_date"] for r in await cur.fetchall()}
    streak_data = calculate_streak(dates, today)

    # 4. extended_today: первый завершённый урок за эту дату
    cur = await db.execute(
        """SELECT COUNT(*) as cnt FROM lessons 
           WHERE learning_profile_id = %s AND status = 'completed' 
             AND completed_local_date = %s AND completed_at < %s""",
        [profile_id, lesson["completed_local_date"], lesson["completed_at"]],
    )
    earlier_count = (await cur.fetchone())["cnt"]
    extended_today = earlier_count == 0

    streak_data["extended_today"] = extended_today

    return {
        "lesson_id": lesson_id,
        "lesson_number": lesson["lesson_number"],
        "exercises_total": len(exercises),
        "words_total": words_total,
        "correct_count": correct,
        "incorrect_count": incorrect,
        "typo_count": typo,
        "accuracy": accuracy,
        "time_spent": time_spent,
        "new_words_learned": new_words,
        "streak_current": streak_data["current"],
        "streak_longest": streak_data["longest"],
    }
