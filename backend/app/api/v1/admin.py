"""
101slovo — Административные эндпоинты.
Словари, жалобы, пользователи.
"""

import secrets
from typing import Literal, Optional

import bcrypt
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from psycopg import AsyncConnection
from pydantic import BaseModel

from app.api.deps import get_current_admin_user_id, get_db
from app.services.admin_audit import log_admin_action
from app.services.dictionary_import import import_dictionary

router = APIRouter()


# ==================== Dictionaries ====================


@router.post("/dictionaries/import")
async def import_dictionary_endpoint(
    file: UploadFile = File(...),
    dry_run: bool = Query(False, description="Dry run mode - validate only"),
    admin_id: int = Depends(get_current_admin_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Импорт словаря из JSON файла.
    
    Поддерживает dry_run режим для предварительной проверки без записи в БД.
    """
    # Валидация типа файла
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_file_type: only .json files allowed",
        )
    
    # Чтение содержимого
    content = await file.read()
    
    # Валидация размера (макс 10 МБ)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_too_large: maximum 10MB",
        )
    
    try:
        result = await import_dictionary(db, admin_id, content, dry_run)
        return result
    except ValueError as e:
        error_msg = str(e)
        if error_msg.startswith("invalid_json"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )


@router.get("/dictionaries")
async def list_dictionaries_admin(
    admin_id: int = Depends(get_current_admin_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """Список всех словарей с количеством слов."""
    cur = await db.execute(
        """SELECT d.id, d.code, d.name, d.description, d.created_at,
                  COUNT(w.id) as words_count
           FROM dictionaries d
           LEFT JOIN words w ON d.id = ANY(w.dictionary_ids)
           GROUP BY d.id, d.code, d.name, d.description, d.created_at
           ORDER BY d.name"""
    )
    return await cur.fetchall()


# ==================== Reports ====================


class ReportUpdateRequest(BaseModel):
    status: Literal["processed"]
    admin_note: Optional[str] = None


@router.get("/reports")
async def list_reports(
    status_filter: Optional[Literal["new", "processed"]] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    admin_id: int = Depends(get_current_admin_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Список жалоб на предложения с фильтрацией и пагинацией.
    """
    where_clause = ""
    params = []
    
    if status_filter:
        where_clause = "WHERE sr.status = %s"
        params.append(status_filter)
    
    # Подсчет общего количества
    count_query = f"SELECT COUNT(*) as cnt FROM sentence_reports sr {where_clause}"
    cur = await db.execute(count_query, params)
    total = (await cur.fetchone())["cnt"]
    
    # Получение данных
    offset = (page - 1) * page_size
    data_query = f"""
        SELECT sr.id, sr.user_id, sr.exercise_id, sr.reason, sr.comment,
               sr.status, sr.admin_note, sr.created_at, sr.updated_at,
               le.target_sentence, le.reference_translation, le.user_translation,
               le.target_words
        FROM sentence_reports sr
        JOIN lesson_exercises le ON le.id = sr.exercise_id
        {where_clause}
        ORDER BY sr.created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    cur = await db.execute(data_query, params)
    reports = await cur.fetchall()
    
    return {
        "items": reports,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.patch("/reports/{report_id}")
async def update_report(
    report_id: int,
    req: ReportUpdateRequest,
    admin_id: int = Depends(get_current_admin_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Обновление статуса жалобы (обработка).
    """
    async with db.transaction():
        # Проверяем существование жалобы
        cur = await db.execute(
            "SELECT id, status FROM sentence_reports WHERE id = %s FOR UPDATE",
            [report_id],
        )
        report = await cur.fetchone()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="report_not_found",
            )
        
        # Обновляем статус
        await db.execute(
            """UPDATE sentence_reports
               SET status = %s, admin_note = %s, updated_at = now()
               WHERE id = %s""",
            [req.status, req.admin_note, report_id],
        )
        
        # Логируем действие
        await log_admin_action(
            db,
            admin_id=admin_id,
            action="report_processed",
            target_type="report",
            target_id=str(report_id),
            details={"status": req.status, "admin_note": req.admin_note},
        )
    
    return {"status": "ok"}


# ==================== Users ====================


@router.get("/users")
async def list_users(
    q: Optional[str] = Query(None, max_length=254, description="Search by email"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    admin_id: int = Depends(get_current_admin_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Список пользователей с поиском по email и пагинацией.
    """
    where_clause = ""
    params = []
    
    if q:
        where_clause = "WHERE email ILIKE %s"
        params.append(f"%{q}%")
    
    # Подсчет общего количества
    count_query = f"SELECT COUNT(*) as cnt FROM users {where_clause}"
    cur = await db.execute(count_query, params)
    total = (await cur.fetchone())["cnt"]
    
    # Получение данных
    offset = (page - 1) * page_size
    data_query = f"""
        SELECT id, email, timezone, is_onboarded, is_admin, created_at
        FROM users
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    cur = await db.execute(data_query, params)
    users = await cur.fetchall()
    
    return {
        "items": users,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    admin_id: int = Depends(get_current_admin_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Сброс пароля пользователя.
    
    Генерирует временный пароль и отзывает все refresh-токены.
    Временный пароль возвращается в ответе (показывается один раз).
    """
    async with db.transaction():
        # Проверяем существование пользователя
        cur = await db.execute("SELECT id, email FROM users WHERE id = %s", [user_id])
        user = await cur.fetchone()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user_not_found",
            )
        
        # Генерируем временный пароль
        temp_password = secrets.token_urlsafe(12)
        password_hash = bcrypt.hashpw(temp_password.encode(), bcrypt.gensalt()).decode()
        
        # Обновляем пароль
        await db.execute(
            "UPDATE users SET password_hash = %s, updated_at = now() WHERE id = %s",
            [password_hash, user_id],
        )
        
        # Отзываем все refresh-токены
        await db.execute(
            "UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = %s AND revoked_at IS NULL",
            [user_id],
        )
        
        # Логируем действие
        await log_admin_action(
            db,
            admin_id=admin_id,
            action="user_password_reset",
            target_type="user",
            target_id=str(user_id),
            details={"email": user["email"]},
        )
    
    # Возвращаем временный пароль (показывается один раз)
    return {
        "status": "ok",
        "user_id": user_id,
        "temporary_password": temp_password,
    }
