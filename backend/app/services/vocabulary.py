"""
101slovo — Сервис словаря пользователя.
Список слов, карточка слова, смена статуса.
"""

from psycopg import AsyncConnection


async def get_vocabulary_list(
    db: AsyncConnection,
    *,
    profile_id: int,
    status: str | None = None,
    query: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    GET /vocabulary/list — список слов пользователя.
    
    Параметры:
    - status: фильтр по статусу (active/mastered/ignored)
    - query: поиск по lemma или translations (ILIKE)
    - page/page_size: пагинация
    
    Возвращает:
    - items: список слов с due_in_lessons
    - total: общее количество
    - page/page_size: параметры пагинации
    """
    # Получаем last_lesson_number для расчёта due_in_lessons
    cur = await db.execute(
        "SELECT last_lesson_number FROM learning_profiles WHERE id = %s",
        [profile_id],
    )
    profile = await cur.fetchone()
    last_lesson_number = profile["last_lesson_number"] if profile else 0

    # Базовый запрос
    where_clauses = ["uw.learning_profile_id = %s"]
    params = [profile_id]

    if status and status in ("active", "mastered", "ignored"):
        where_clauses.append("uw.status = %s")
        params.append(status)

    if query:
        where_clauses.append(
            """(w.lemma ILIKE '%%' || %s || '%%' 
               OR EXISTS (SELECT 1 FROM unnest(w.translations) AS t WHERE t ILIKE '%%' || %s || '%%'))"""
        )
        params.extend([query, query])

    where_sql = " AND ".join(where_clauses)

    # Подсчёт общего количества
    count_query = f"""
        SELECT COUNT(*) as cnt
        FROM user_words uw
        JOIN words w ON w.id = uw.word_id
        WHERE {where_sql}
    """
    cur = await db.execute(count_query, params)
    total = (await cur.fetchone())["cnt"]

    # Получение данных
    offset = (page - 1) * page_size
    data_query = f"""
        SELECT w.id as word_id, w.lemma, w.pos, w.translations, 
               uw.status, uw.stage, uw.due_lesson_number
        FROM user_words uw
        JOIN words w ON w.id = uw.word_id
        WHERE {where_sql}
        ORDER BY w.lemma ASC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    cur = await db.execute(data_query, params)
    rows = await cur.fetchall()

    items = []
    for r in rows:
        due_in_lessons = 0
        if r["status"] == "active" and r["due_lesson_number"] is not None:
            due_in_lessons = max(r["due_lesson_number"] - last_lesson_number, 0)

        items.append(
            {
                "word_id": r["word_id"],
                "lemma": r["lemma"],
                "pos": r["pos"],
                "translations": r["translations"],
                "status": r["status"],
                "stage": r["stage"],
                "due_in_lessons": due_in_lessons,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_vocabulary_word(
    db: AsyncConnection, *, profile_id: int, word_id: int
) -> dict:
    """
    GET /vocabulary/word/{id} — карточка слова.
    
    Возвращает полную информацию о слове с due_in_lessons.
    """
    # Получаем last_lesson_number
    cur = await db.execute(
        "SELECT last_lesson_number FROM learning_profiles WHERE id = %s",
        [profile_id],
    )
    profile = await cur.fetchone()
    last_lesson_number = profile["last_lesson_number"] if profile else 0

    # Получаем слово из user_words
    cur = await db.execute(
        """SELECT w.id as word_id, w.lemma, w.pos, w.translations, w.level,
                  uw.status, uw.stage, uw.due_lesson_number, uw.last_reviewed_at, uw.source
           FROM user_words uw
           JOIN words w ON w.id = uw.word_id
           WHERE uw.learning_profile_id = %s AND uw.word_id = %s""",
        [profile_id, word_id],
    )
    row = await cur.fetchone()
    if not row:
        raise ValueError("word_not_found")

    due_in_lessons = 0
    if row["status"] == "active" and row["due_lesson_number"] is not None:
        due_in_lessons = max(row["due_lesson_number"] - last_lesson_number, 0)

    return {
        "word_id": row["word_id"],
        "lemma": row["lemma"],
        "pos": row["pos"],
        "translations": row["translations"],
        "level": row["level"],
        "status": row["status"],
        "stage": row["stage"],
        "due_in_lessons": due_in_lessons,
        "last_reviewed_at": (
            row["last_reviewed_at"].isoformat() if row["last_reviewed_at"] else None
        ),
        "source": row["source"],
    }


async def change_word_status(
    db: AsyncConnection,
    *,
    profile_id: int,
    word_id: int,
    new_status: str,
) -> dict:
    """
    PATCH /vocabulary/word/{id}/status — смена статуса слова.
    
    Переходы:
    - active → ignored (убрать из повторения)
    - ignored → active (вернуть в повторение)
    - mastered → active (вернуть в повторение)
    
    Идемпотентность: если уже в целевом статусе — успех.
    """
    # Получаем last_lesson_number
    cur = await db.execute(
        "SELECT last_lesson_number FROM learning_profiles WHERE id = %s",
        [profile_id],
    )
    profile = await cur.fetchone()
    if not profile:
        raise ValueError("profile_not_found")
    last_lesson_number = profile["last_lesson_number"]

    async with db.transaction():
        # Блокируем строку
        cur = await db.execute(
            """SELECT id, status FROM user_words 
               WHERE learning_profile_id = %s AND word_id = %s FOR UPDATE""",
            [profile_id, word_id],
        )
        uw = await cur.fetchone()
        if not uw:
            raise ValueError("word_not_found")

        current_status = uw["status"]

        # Идемпотентность: если уже в целевом статусе
        if current_status == new_status:
            return {"status": "ok", "word_id": word_id, "status_value": new_status}

        # Валидация переходов
        valid_transitions = {
            ("active", "ignored"),
            ("ignored", "active"),
            ("mastered", "active"),
        }

        if (current_status, new_status) not in valid_transitions:
            raise ValueError("invalid_transition")

        # Применяем переход
        if current_status == "active" and new_status == "ignored":
            await db.execute(
                """UPDATE user_words 
                   SET status = 'ignored', due_lesson_number = NULL, updated_at = now()
                   WHERE id = %s""",
                [uw["id"]],
            )
        elif current_status in ("ignored", "mastered") and new_status == "active":
            new_due = last_lesson_number + 1
            await db.execute(
                """UPDATE user_words 
                   SET status = 'active', stage = 0, due_lesson_number = %s, updated_at = now()
                   WHERE id = %s""",
                [new_due, uw["id"]],
            )

    return {"status": "ok", "word_id": word_id, "status_value": new_status}
