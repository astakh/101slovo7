"""
101slovo — Роутер словаря пользователя.
Список слов, карточка слова, смена статуса.
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg import AsyncConnection
from pydantic import BaseModel

from app.api.deps import get_current_user_id, get_db
from app.services.vocabulary import (
    change_word_status,
    get_vocabulary_list,
    get_vocabulary_word,
)

router = APIRouter()


class StatusChangeRequest(BaseModel):
    status: Literal["active", "ignored"]


@router.get("/list")
async def vocabulary_list(
    status_filter: Optional[Literal["active", "mastered", "ignored"]] = Query(
        None, alias="status"
    ),
    q: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user_id: int = Depends(get_current_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Список слов пользователя с фильтрацией и пагинацией.
    
    Параметры:
    - status: фильтр по статусу (active/mastered/ignored)
    - q: поиск по lemma или translations (ILIKE)
    - page/page_size: пагинация (макс. 50 на страницу)
    """
    cur = await db.execute(
        "SELECT id FROM learning_profiles WHERE user_id = %s", [user_id]
    )
    profile = await cur.fetchone()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="onboarding_required",
        )

    return await get_vocabulary_list(
        db,
        profile_id=profile["id"],
        status=status_filter,
        query=q,
        page=page,
        page_size=page_size,
    )


@router.get("/word/{word_id}")
async def vocabulary_word(
    word_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Карточка слова.
    
    Возвращает полную информацию о слове с due_in_lessons.
    """
    cur = await db.execute(
        "SELECT id FROM learning_profiles WHERE user_id = %s", [user_id]
    )
    profile = await cur.fetchone()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="onboarding_required",
        )

    try:
        return await get_vocabulary_word(
            db, profile_id=profile["id"], word_id=word_id
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="word_not_found",
        )


@router.patch("/word/{word_id}/status")
async def vocabulary_change_status(
    word_id: int,
    req: StatusChangeRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Смена статуса слова.
    
    Переходы:
    - active → ignored (убрать из повторения)
    - ignored → active (вернуть в повторение)
    - mastered → active (вернуть в повторение)
    
    Идемпотентность: если уже в целевом статусе — успех.
    """
    cur = await db.execute(
        "SELECT id FROM learning_profiles WHERE user_id = %s", [user_id]
    )
    profile = await cur.fetchone()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="onboarding_required",
        )

    try:
        return await change_word_status(
            db,
            profile_id=profile["id"],
            word_id=word_id,
            new_status=req.status,
        )
    except ValueError as e:
        error_code = str(e)
        status_map = {
            "word_not_found": (404, "word_not_found"),
            "invalid_transition": (409, "invalid_transition"),
            "profile_not_found": (404, "profile_not_found"),
        }
        http_status, code = status_map.get(error_code, (400, error_code))
        raise HTTPException(status_code=http_status, detail=code)
