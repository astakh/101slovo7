"""
101slovo — Роутер онбординга.
Завершение онбординга, получение списка словарей и лимитов.
"""
import json
import zoneinfo
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import AsyncConnection
from app.api.deps import get_current_user_id, get_db
from app.config import settings
from app.schemas.onboarding import (
    DictionaryResponse,
    OnboardingRequest,
    OnboardingResponse,
    OnboardingLimitsResponse,
)

router = APIRouter()


@router.post("/complete", response_model=OnboardingResponse)
async def complete_onboarding(
    req: OnboardingRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Завершение онбординга.
    - Валидирует часовой пояс и лимиты из .env
    - Создаёт профиль обучения с настройками пользователя
    - Привязывает пользователя к словарю
    - Логирует событие onboarding_completed
    """
    # 1. Валидация часового пояса
    if req.timezone not in zoneinfo.available_timezones():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid_timezone",
        )

    # 2. Динамическая валидация лимитов из .env
    if req.words_per_lesson > settings.WORDS_PER_LESSON_MAX:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="words_per_lesson_too_high",
        )
    if req.daily_lesson_limit > settings.DAILY_LESSON_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="daily_lesson_limit_too_high",
        )

    async with db.transaction():
        # 3. Проверка статуса пользователя
        cur = await db.execute(
            "SELECT is_onboarded FROM users WHERE id = %s",
            [user_id],
        )
        user = await cur.fetchone()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
        if user["is_onboarded"]:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="already_onboarded")

        # 4. Проверка наличия выбранного словаря
        cur_dict = await db.execute("SELECT id FROM dictionaries WHERE id = %s", [req.dictionary_id])
        if not await cur_dict.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dictionary_not_found")

        # 5. Обновление пользователя
        await db.execute(
            """UPDATE users
            SET timezone = %s, is_onboarded = true, updated_at = now()
            WHERE id = %s""",
            [req.timezone, user_id],
        )

        # 6. Создание профиля обучения
        await db.execute(
            """INSERT INTO learning_profiles
            (user_id, level, dictionary_id, daily_lesson_limit, words_per_lesson)
            VALUES (%s, %s, %s, %s, %s)""",
            [
                user_id,
                req.level,
                req.dictionary_id,
                req.daily_lesson_limit,
                req.words_per_lesson,
            ],
        )

        # 7. Логирование события
        await db.execute(
            "INSERT INTO events (user_id, type, payload) VALUES (%s, %s, %s)",
            [
                user_id,
                "onboarding_completed",
                json.dumps({
                    "level": req.level,
                    "timezone": req.timezone,
                    "words_per_lesson": req.words_per_lesson,
                    "daily_lesson_limit": req.daily_lesson_limit,
                }),
            ],
        )

    return OnboardingResponse(status="ok")


@router.get("/dictionaries", response_model=list[DictionaryResponse])
async def get_dictionaries(
    db: AsyncConnection = Depends(get_db),
):
    """Получение списка доступных словарей."""
    cur = await db.execute(
        "SELECT id, code, name, description FROM dictionaries ORDER BY name"
    )
    rows = await cur.fetchall()
    return [DictionaryResponse(**row) for row in rows]


@router.get("/limits", response_model=OnboardingLimitsResponse)
async def get_onboarding_limits():
    """
    Получение лимитов для онбординга.
    Значения берутся из переменных окружения (.env).
    """
    return OnboardingLimitsResponse(
        words_per_lesson_min=settings.WORDS_PER_LESSON_MIN,
        words_per_lesson_max=settings.WORDS_PER_LESSON_MAX,
        daily_lesson_limit_max=settings.DAILY_LESSON_LIMIT_MAX,
    )