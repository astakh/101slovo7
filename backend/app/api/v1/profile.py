"""
101slovo — Роутер профиля и статистики.
Heatmap, точность, сводка слов.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import AsyncConnection

from app.api.deps import get_current_user_id, get_db
from app.schemas.profile import HeatmapEntry, ProfileStatsResponse
from app.utils.datetime import calculate_streak, get_user_today

router = APIRouter()


@router.get("/stats", response_model=ProfileStatsResponse)
async def get_profile_stats(
    user_id: int = Depends(get_current_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Получение полной статистики профиля.
    
    Возвращает:
    - Стрик (current/longest)
    - Heatmap за 12 месяцев
    - Точность за 30 дней и всё время
    - Слова по статусам
    - Количество завершённых уроков
    """
    # Получаем профиль и таймзону
    cur = await db.execute(
        """SELECT u.timezone, lp.id as profile_id 
           FROM users u 
           JOIN learning_profiles lp ON lp.user_id = u.id 
           WHERE u.id = %s""",
        [user_id],
    )
    row = await cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="profile_not_found",
        )

    profile_id = row["profile_id"]
    user_tz = row["timezone"]
    today = get_user_today(user_tz)

    # 1. Heatmap за 12 месяцев
    twelve_months_ago = today - timedelta(days=365)
    cur = await db.execute(
        """SELECT completed_local_date as d, COUNT(*) as cnt 
           FROM lessons 
           WHERE learning_profile_id = %s 
             AND status = 'completed' 
             AND completed_local_date >= %s
           GROUP BY completed_local_date""",
        [profile_id, twelve_months_ago],
    )
    heatmap = [HeatmapEntry(date=r["d"], count=r["cnt"]) for r in await cur.fetchall()]

    # 2. Стрик
    cur = await db.execute(
        """SELECT DISTINCT completed_local_date 
           FROM lessons 
           WHERE learning_profile_id = %s AND status = 'completed'""",
        [profile_id],
    )
    dates = {r["completed_local_date"] for r in await cur.fetchall()}
    streak_data = calculate_streak(dates, today)

    # 3. Точность (все время и 30 дней)
    async def get_accuracy(days_ago: int | None = None) -> float:
        query = """
            SELECT COUNT(*) as total,
                   COUNT(*) FILTER (WHERE elem->>'result' IN ('correct', 'typo')) as success
            FROM lesson_exercises le
            JOIN lessons l ON le.lesson_id = l.id
            CROSS JOIN LATERAL jsonb_array_elements(le.target_words) as elem
            WHERE l.learning_profile_id = %s AND le.status = 'evaluated'
        """
        params = [profile_id]
        if days_ago:
            query += " AND l.completed_local_date >= %s"
            params.append(today - timedelta(days=days_ago))

        cur = await db.execute(query, params)
        r = await cur.fetchone()
        if r["total"] == 0:
            return 0.0
        return round(r["success"] / r["total"], 4)

    accuracy_30 = await get_accuracy(30)
    accuracy_all = await get_accuracy()

    # 4. Слова по статусам
    cur = await db.execute(
        """SELECT status, COUNT(*) as cnt 
           FROM user_words 
           WHERE learning_profile_id = %s 
           GROUP BY status""",
        [profile_id],
    )
    words_dict = {r["status"]: r["cnt"] for r in await cur.fetchall()}

    # 5. Завершённые уроки
    cur = await db.execute(
        """SELECT COUNT(*) as cnt 
           FROM lessons 
           WHERE learning_profile_id = %s AND status = 'completed'""",
        [profile_id],
    )
    completed_lessons = (await cur.fetchone())["cnt"]

    return ProfileStatsResponse(
        streak_current=streak_data["current"],
        streak_longest=streak_data["longest"],
        heatmap=heatmap,
        accuracy_30_days=accuracy_30,
        accuracy_all_time=accuracy_all,
        words_active=words_dict.get("active", 0),
        words_mastered=words_dict.get("mastered", 0),
        words_ignored=words_dict.get("ignored", 0),
        completed_lessons=completed_lessons,
    )
