"""
101slovo — Роутер Dashboard.
Главный экран приложения с сводкой, стриком и CTA.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import AsyncConnection

from app.api.deps import get_current_user_id, get_db
from app.schemas.dashboard import (
    DashboardDictionary,
    DashboardProfile,
    DashboardResponse,
    DashboardResume,
    DashboardStreak,
    DashboardWords,
)
from app.utils.datetime import calculate_streak, get_resets_at, get_user_today

router = APIRouter()


@router.get("/summary", response_model=DashboardResponse)
async def get_dashboard_summary(
    user_id: int = Depends(get_current_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Получение сводки для главного экрана.
    
    Возвращает:
    - Профиль (уровень, словарь)
    - Текущая дата и время сброса лимита
    - Количество уроков сегодня и лимит
    - CTA (start/resume/limit_reached)
    - Незавершённый урок (если есть)
    - Сводка слов (active/mastered/ignored)
    - Стрик (current/longest/today_done)
    """
    # 1. Получаем пользователя и профиль
    cur = await db.execute(
        """SELECT u.timezone, u.is_onboarded, lp.id as profile_id, lp.level, 
                  lp.dictionary_id, lp.daily_lesson_limit, lp.words_per_lesson, 
                  lp.last_lesson_number, d.name as dictionary_name
           FROM users u
           JOIN learning_profiles lp ON lp.user_id = u.id
           JOIN dictionaries d ON d.id = lp.dictionary_id
           WHERE u.id = %s""",
        [user_id],
    )
    row = await cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="profile_not_found",
        )
    if not row["is_onboarded"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="onboarding_required",
        )

    user_tz = row["timezone"]
    profile_id = row["profile_id"]
    today = get_user_today(user_tz)

    # 2. Уроки сегодня
    cur = await db.execute(
        """SELECT COUNT(*) as cnt 
           FROM lessons 
           WHERE learning_profile_id = %s AND started_local_date = %s""",
        [profile_id, today],
    )
    lessons_today = (await cur.fetchone())["cnt"]

    # 3. Незавершённый урок (resume)
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
    resume = None
    if resume_row:
        resume = DashboardResume(
            lesson_id=resume_row["id"],
            lesson_number=resume_row["lesson_number"],
            exercises_done=resume_row["exercises_done"],
            exercises_total=resume_row["exercises_total"],
        )

    # 4. Сводка слов
    cur = await db.execute(
        """SELECT status, COUNT(*) as cnt 
           FROM user_words 
           WHERE learning_profile_id = %s 
           GROUP BY status""",
        [profile_id],
    )
    words_dict = {r["status"]: r["cnt"] for r in await cur.fetchall()}
    words = DashboardWords(
        active=words_dict.get("active", 0),
        mastered=words_dict.get("mastered", 0),
        ignored=words_dict.get("ignored", 0),
    )

    # 5. Стрик
    cur = await db.execute(
        """SELECT DISTINCT completed_local_date 
           FROM lessons 
           WHERE learning_profile_id = %s 
             AND status = 'completed' 
             AND completed_local_date IS NOT NULL""",
        [profile_id],
    )
    dates = {r["completed_local_date"] for r in await cur.fetchall()}
    streak_data = calculate_streak(dates, today)

    # 6. Определяем CTA
    if resume:
        cta = "resume"
    elif lessons_today >= row["daily_lesson_limit"]:
        cta = "limit_reached"
    else:
        cta = "start"

    resets_at = get_resets_at(user_tz)

    return DashboardResponse(
        profile=DashboardProfile(
            level=row["level"],
            dictionary=DashboardDictionary(
                id=row["dictionary_id"],
                name=row["dictionary_name"],
            ),
        ),
        today=today,
        lessons_today=lessons_today,
        daily_lesson_limit=row["daily_lesson_limit"],
        resets_at=resets_at,
        cta=cta,
        resume=resume,
        words=words,
        streak=DashboardStreak(**streak_data),
    )
