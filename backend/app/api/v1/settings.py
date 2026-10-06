"""
101slovo — Роутер настроек обучения.
Профиль, словари, смена часового пояса.
"""

import zoneinfo
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import AsyncConnection

from app.api.deps import get_current_user_id, get_db
from app.config import settings
from app.schemas.settings import (
    LearningProfileResponse,
    LearningProfileUpdate,
    TimezoneResponse,
    TimezoneUpdate,
)
from app.utils.datetime import calculate_streak, get_resets_at, get_user_today

router = APIRouter()


@router.get("/learning-profile", response_model=LearningProfileResponse)
async def get_learning_profile(
    user_id: int = Depends(get_current_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Получение профиля обучения с настройками и статистикой.
    """
    cur = await db.execute(
        """SELECT lp.id as profile_id, lp.level, lp.dictionary_id, lp.daily_lesson_limit, 
                  lp.words_per_lesson, d.code, d.name as dict_name, d.description
           FROM learning_profiles lp
           JOIN dictionaries d ON d.id = lp.dictionary_id
           WHERE lp.user_id = %s""",
        [user_id],
    )
    row = await cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="profile_not_found",
        )

    profile_id = row["profile_id"]

    # Статистика для настроек
    cur = await db.execute(
        """SELECT status, COUNT(*) as cnt 
           FROM user_words 
           WHERE learning_profile_id = %s 
           GROUP BY status""",
        [profile_id],
    )
    words_dict = {r["status"]: r["cnt"] for r in await cur.fetchall()}

    cur = await db.execute(
        """SELECT COUNT(*) as cnt 
           FROM lessons 
           WHERE learning_profile_id = %s AND status = 'completed'""",
        [profile_id],
    )
    completed_lessons = (await cur.fetchone())["cnt"]

    # Точность (всё время)
    cur = await db.execute(
        """SELECT COUNT(*) as total,
                  COUNT(*) FILTER (WHERE elem->>'result' IN ('correct', 'typo')) as success
           FROM lesson_exercises le
           JOIN lessons l ON le.lesson_id = l.id
           CROSS JOIN LATERAL jsonb_array_elements(le.target_words) as elem
           WHERE l.learning_profile_id = %s AND le.status = 'evaluated'""",
        [profile_id],
    )
    acc_row = await cur.fetchone()
    accuracy_all = (
        round(acc_row["success"] / acc_row["total"], 4) if acc_row["total"] > 0 else 0.0
    )

    # Точность за 30 дней
    cur = await db.execute("SELECT timezone FROM users WHERE id = %s", [user_id])
    user_tz = (await cur.fetchone())["timezone"]
    today = get_user_today(user_tz)
    cur = await db.execute(
        """SELECT COUNT(*) as total,
                  COUNT(*) FILTER (WHERE elem->>'result' IN ('correct', 'typo')) as success
           FROM lesson_exercises le
           JOIN lessons l ON le.lesson_id = l.id
           CROSS JOIN LATERAL jsonb_array_elements(le.target_words) as elem
           WHERE l.learning_profile_id = %s AND le.status = 'evaluated'
             AND l.completed_local_date >= %s""",
        [profile_id, today - timedelta(days=30)],
    )
    acc30_row = await cur.fetchone()
    accuracy_30 = (
        round(acc30_row["success"] / acc30_row["total"], 4) if acc30_row["total"] > 0 else 0.0
    )

    return LearningProfileResponse(
        level=row["level"],
        dictionary={
            "id": row["dictionary_id"],
            "code": row["code"],
            "name": row["dict_name"],
            "description": row["description"],
        },
        daily_lesson_limit=row["daily_lesson_limit"],
        daily_lesson_limit_max=settings.DAILY_LESSON_LIMIT_MAX,
        words_per_lesson=row["words_per_lesson"],
        words_per_lesson_min=settings.WORDS_PER_LESSON_MIN,
        words_per_lesson_max=settings.WORDS_PER_LESSON_MAX,
        stats={
            "words": {
                "active": words_dict.get("active", 0),
                "mastered": words_dict.get("mastered", 0),
                "ignored": words_dict.get("ignored", 0),
            },
            "accuracy_all_time": accuracy_all,
            "accuracy_30_days": accuracy_30,
            "completed_lessons": completed_lessons,
        },
    )


@router.patch("/learning-profile")
async def update_learning_profile(
    req: LearningProfileUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Обновление профиля обучения.
    
    Можно изменить:
    - level (A1/A2/B1/B2)
    - dictionary_id
    - daily_lesson_limit
    - words_per_lesson
    """
    async with db.transaction():
        # Получаем текущий профиль
        cur = await db.execute(
            "SELECT id FROM learning_profiles WHERE user_id = %s FOR UPDATE",
            [user_id],
        )
        profile = await cur.fetchone()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="profile_not_found",
            )
        profile_id = profile["id"]

        updates = []
        params = []

        if req.level is not None:
            updates.append("level = %s")
            params.append(req.level)

        if req.dictionary_id is not None:
            # Проверяем существование словаря
            cur = await db.execute(
                "SELECT id FROM dictionaries WHERE id = %s",
                [req.dictionary_id],
            )
            if not await cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="dictionary_not_found",
                )
            updates.append("dictionary_id = %s")
            params.append(req.dictionary_id)

        if req.daily_lesson_limit is not None:
            if req.daily_lesson_limit > settings.DAILY_LESSON_LIMIT_MAX:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="daily_lesson_limit_too_high",
                )
            updates.append("daily_lesson_limit = %s")
            params.append(req.daily_lesson_limit)

        if req.words_per_lesson is not None:
            if (
                req.words_per_lesson < settings.WORDS_PER_LESSON_MIN
                or req.words_per_lesson > settings.WORDS_PER_LESSON_MAX
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="words_per_lesson_out_of_range",
                )
            updates.append("words_per_lesson = %s")
            params.append(req.words_per_lesson)

        if updates:
            updates.append("updated_at = now()")
            params.append(profile_id)
            await db.execute(
                f"UPDATE learning_profiles SET {', '.join(updates)} WHERE id = %s",
                params,
            )

    return {"status": "ok"}


@router.get("/dictionaries")
async def list_dictionaries(db: AsyncConnection = Depends(get_db)):
    """
    Получение списка словарей с количеством слов.
    """
    cur = await db.execute(
        """SELECT d.id, d.code, d.name, d.description,
                  COUNT(w.id) as words_total
           FROM dictionaries d
           LEFT JOIN words w ON d.id = ANY(w.dictionary_ids)
           GROUP BY d.id, d.code, d.name, d.description
           ORDER BY d.name"""
    )
    rows = await cur.fetchall()

    result = []
    for r in rows:
        result.append(
            {
                "id": r["id"],
                "code": r["code"],
                "name": r["name"],
                "description": r["description"],
                "is_default": r["code"] == settings.DEFAULT_DICTIONARY_CODE,
                "words_total": r["words_total"],
            }
        )
    return result


@router.patch("/settings/timezone", response_model=TimezoneResponse)
async def update_timezone(
    req: TimezoneUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Смена часового пояса.
    
    Ограничения:
    - Валидация IANA timezone
    - Идемпотентность (если тот же пояс — просто возвращаем данные)
    - Лимит: не чаще раза в 7 дней
    """
    # 1. Валидация IANA
    if req.timezone not in zoneinfo.available_timezones():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid_timezone",
        )

    async with db.transaction():
        cur = await db.execute(
            "SELECT timezone, timezone_changed_at FROM users WHERE id = %s FOR UPDATE",
            [user_id],
        )
        user = await cur.fetchone()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user_not_found",
            )

        # Идемпотентность
        if user["timezone"] == req.timezone:
            today = get_user_today(req.timezone)
            resets_at = get_resets_at(req.timezone)

            # Получаем данные для ответа
            cur = await db.execute(
                "SELECT lp.id FROM learning_profiles lp WHERE lp.user_id = %s",
                [user_id],
            )
            profile_id = (await cur.fetchone())["id"]

            cur = await db.execute(
                """SELECT COUNT(*) as cnt 
                   FROM lessons 
                   WHERE learning_profile_id = %s AND started_local_date = %s""",
                [profile_id, today],
            )
            lessons_today = (await cur.fetchone())["cnt"]

            cur = await db.execute(
                """SELECT DISTINCT completed_local_date 
                   FROM lessons 
                   WHERE learning_profile_id = %s AND status = 'completed'""",
                [profile_id],
            )
            dates = {r["completed_local_date"] for r in await cur.fetchall()}
            streak_data = calculate_streak(dates, today)

            return TimezoneResponse(
                today=today.isoformat(),
                lessons_today=lessons_today,
                resets_at=resets_at.isoformat(),
                streak=streak_data,
            )

        # Проверка 7 дней
        if user["timezone_changed_at"]:
            days_passed = (
                datetime.now(timezone.utc) - user["timezone_changed_at"]
            ).days
            if days_passed < 7:
                available_at = user["timezone_changed_at"] + timedelta(days=7)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "timezone_change_too_soon",
                        "available_at": available_at.isoformat(),
                    },
                )

        # Обновляем
        await db.execute(
            """UPDATE users 
               SET timezone = %s, timezone_changed_at = now(), updated_at = now() 
               WHERE id = %s""",
            [req.timezone, user_id],
        )

    # Возвращаем новые данные
    today = get_user_today(req.timezone)
    resets_at = get_resets_at(req.timezone)

    cur = await db.execute(
        "SELECT id FROM learning_profiles WHERE user_id = %s",
        [user_id],
    )
    profile_id = (await cur.fetchone())["id"]

    cur = await db.execute(
        """SELECT COUNT(*) as cnt 
           FROM lessons 
           WHERE learning_profile_id = %s AND started_local_date = %s""",
        [profile_id, today],
    )
    lessons_today = (await cur.fetchone())["cnt"]

    cur = await db.execute(
        """SELECT DISTINCT completed_local_date 
           FROM lessons 
           WHERE learning_profile_id = %s AND status = 'completed'""",
        [profile_id],
    )
    dates = {r["completed_local_date"] for r in await cur.fetchall()}
    streak_data = calculate_streak(dates, today)

    return TimezoneResponse(
        today=today.isoformat(),
        lessons_today=lessons_today,
        resets_at=resets_at.isoformat(),
        streak=streak_data,
    )
