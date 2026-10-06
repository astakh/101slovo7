"""
101slovo — Логирование вызовов LLM в таблицу llm_calls.
"""

import json
import logging

from psycopg import AsyncConnection

logger = logging.getLogger(__name__)


async def log_llm_call(
    db: AsyncConnection,
    *,
    purpose: str,
    user_id: int | None,
    lesson_id: int | None,
    exercise_id: int | None,
    attempt: int,
    request: dict,
    response_raw: str | None,
    response_json: dict | None,
    status: str,
    http_status: int | None,
    latency_ms: int,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    error_code: str | None,
) -> None:
    """
    Записывает вызов LLM в таблицу llm_calls.
    
    Args:
        db: Соединение с БД
        purpose: Назначение вызова ('generate' | 'evaluate')
        user_id: ID пользователя (если есть)
        lesson_id: ID урока (если есть)
        exercise_id: ID упражнения (если есть)
        attempt: Номер попытки (начинается с 1)
        request: Запрос к LLM (messages, temperature)
        response_raw: Сырой ответ от LLM
        response_json: Распарсенный JSON
        status: Статус вызова ('ok' | 'http_error' | 'timeout' | 'invalid_json' | 'invalid_schema' | 'validation_failed')
        http_status: HTTP-статус ответа
        latency_ms: Время выполнения в миллисекундах
        prompt_tokens: Количество токенов в запросе
        completion_tokens: Количество токенов в ответе
        error_code: Код ошибки (если есть)
    """
    try:
        await db.execute(
            """INSERT INTO llm_calls 
               (purpose, user_id, lesson_id, exercise_id, attempt, 
                request, response_raw, response_json, status, 
                http_status, latency_ms, prompt_tokens, completion_tokens, error_code)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            [
                purpose,
                user_id,
                lesson_id,
                exercise_id,
                attempt,
                json.dumps(request, ensure_ascii=False),
                response_raw,
                json.dumps(response_json, ensure_ascii=False) if response_json else None,
                status,
                http_status,
                latency_ms,
                prompt_tokens,
                completion_tokens,
                error_code,
            ],
        )
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to log LLM call: {e}")
        await db.rollback()
