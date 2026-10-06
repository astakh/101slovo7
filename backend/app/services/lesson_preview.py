"""
101slovo — Сервис подбора слов для урока.
Алгоритм 5.2 из ТЗ: детерминированный подбор слов с учётом due-слов, 
новых слов, уровня профиля и активного словаря.
"""

from psycopg import AsyncConnection

from app.config import settings
from app.utils.datetime import get_resets_at, get_user_today
from app.utils.ranking import compute_seed, sort_by_rank

# Маппинг уровня на уровень ниже (для подбора новых слов)
LEVEL_BELOW = {
    "A1": None,
    "A2": "A1",
    "B1": "A2",
    "B2": "B1",
}


async def get_preview_data(db: AsyncConnection, profile_id: int) -> dict:
    """
    Алгоритм 5.2: Подбор слов для урока.
    
    Возвращает словарь с состоянием урока:
    - state: "resume" | "limit_reached" | "no_words" | "ready"
    - Дополнительные данные в зависимости от state
    
    Логика:
    1. Проверяем незавершённый урок (resume)
    2. Проверяем дневной лимит
    3. Подбираем due-слова (повторение)
    4. Если due меньше N, подбираем новые слова
    5. Возвращаем готовый набор слов для урока
    """
    # 1. Получаем профиль
    cur = await db.execute(
        """SELECT lp.level, lp.dictionary_id, lp.words_per_lesson, 
                  lp.last_lesson_number, lp.daily_lesson_limit,
                  d.code as dictionary_code
           FROM learning_profiles lp
           JOIN dictionaries d ON d.id = lp.dictionary_id
           WHERE lp.id = %s""",
        [profile_id],
    )
    profile = await cur.fetchone()
    if not profile:
        raise ValueError("profile_not_found")

    # 2. Проверяем незавершённый урок (resume)
    cur = await db.execute(
        """SELECT l.id, l.lesson_number,
                  COUNT(le.id) FILTER (WHERE le.status = 'evaluated') as exercises_done,
                  COUNT(le.id) as exercises_total
           FROM lessons l
           LEFT JOIN lesson_exercises le ON le.lesson_id = l.id
           WHERE l.learning_profile_id = %s AND l.status = 'in_progress'
           GROUP BY l.id, l.lesson_number""",
        [profile_id],
    )
    resume_row = await cur.fetchone()
    if resume_row:
        return {
            "state": "resume",
            "lesson_id": resume_row["id"],
            "lesson_number": resume_row["lesson_number"],
            "exercises_done": resume_row["exercises_done"],
            "exercises_total": resume_row["exercises_total"],
        }

    # 3. Проверяем лимит
    # Получаем таймзону пользователя
    cur = await db.execute(
        """SELECT u.timezone FROM users u 
           JOIN learning_profiles lp ON lp.user_id = u.id 
           WHERE lp.id = %s""",
        [profile_id],
    )
    user_tz = (await cur.fetchone())["timezone"]

    today = get_user_today(user_tz)

    cur = await db.execute(
        """SELECT COUNT(*) as cnt 
           FROM lessons 
           WHERE learning_profile_id = %s AND started_local_date = %s""",
        [profile_id, today],
    )
    lessons_today = (await cur.fetchone())["cnt"]

    if lessons_today >= profile["daily_lesson_limit"]:
        resets_at = get_resets_at(user_tz)
        return {
            "state": "limit_reached",
            "resets_at": resets_at.isoformat(),
        }

    # 4. Номер и seed
    next_lesson_number = profile["last_lesson_number"] + 1
    seed = compute_seed(profile_id, next_lesson_number)

    # Определяем N (количество слов в уроке)
    N = profile["words_per_lesson"]
    N = max(settings.WORDS_PER_LESSON_MIN, min(N, settings.WORDS_PER_LESSON_MAX))

    # 5. Due-слова (повторение)
    cur = await db.execute(
        """SELECT uw.word_id, w.lemma, w.pos
           FROM user_words uw
           JOIN words w ON w.id = uw.word_id
           WHERE uw.learning_profile_id = %s
             AND uw.status = 'active'
             AND uw.due_lesson_number <= %s""",
        [profile_id, next_lesson_number],
    )
    due_words = await cur.fetchall()
    due_words = sort_by_rank(due_words, seed)
    due_words = due_words[:N]

    # 6. Новые слова (если due меньше N)
    new_words = []
    dictionary_exhausted = False

    if len(due_words) < N:
        k = N - len(due_words)

        # Определяем допустимые уровни
        profile_level = profile["level"]
        level_below = LEVEL_BELOW.get(profile_level)

        if profile_level == "A1":
            allowed_levels = ["A1"]
        else:
            allowed_levels = [profile_level, level_below] if level_below else [profile_level]

        # Формируем SQL для новых слов
        is_default_dict = profile["dictionary_code"] == settings.DEFAULT_DICTIONARY_CODE

        query = """
            SELECT w.id as word_id, w.lemma, w.pos, w.translations, w.level
            FROM words w
            WHERE %s = ANY(w.dictionary_ids)
              AND w.id NOT IN (
                  SELECT word_id FROM user_words WHERE learning_profile_id = %s
              )
        """
        params = [profile["dictionary_id"], profile_id]

        # Фильтр по уровню
        if is_default_dict:
            # В общем словаре слова без уровня не подбираются
            query += " AND w.level IS NOT NULL AND w.level = ANY(%s)"
            params.append(allowed_levels)
        else:
            # В не-общем словаре слова без уровня допускаются
            query += " AND (w.level IS NULL OR w.level = ANY(%s))"
            params.append(allowed_levels)

        cur = await db.execute(query, params)
        candidates = await cur.fetchall()
        candidates = sort_by_rank(candidates, seed)
        new_words = candidates[:k]

        # Проверяем исчерпание словаря
        if len(due_words) == 0 and len(new_words) == 0:
            return {"state": "no_words"}

        if len(due_words) + len(new_words) < N:
            dictionary_exhausted = True

    # 7. Формируем ответ
    return {
        "state": "ready",
        "lesson_number": next_lesson_number,
        "due_words": [
            {"word_id": w["word_id"], "lemma": w["lemma"], "pos": w["pos"]}
            for w in due_words
        ],
        "new_words": [
            {
                "word_id": w["word_id"],
                "lemma": w["lemma"],
                "pos": w["pos"],
                "translations": w["translations"],
            }
            for w in new_words
        ],
        "dictionary_exhausted": dictionary_exhausted,
    }
