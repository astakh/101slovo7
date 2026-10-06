"""
101slovo — Сервис логирования действий администраторов.
"""

import json
from psycopg import AsyncConnection


async def log_admin_action(
    db: AsyncConnection,
    *,
    admin_id: int,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None,
) -> None:
    """
    Записывает действие администратора в admin_audit_log.
    
    Args:
        db: Соединение с БД
        admin_id: ID администратора
        action: Тип действия (например, 'dictionary_import', 'user_password_reset')
        target_type: Тип объекта (например, 'dictionary', 'user')
        target_id: ID объекта
        details: Дополнительные детали в JSON формате
    """
    await db.execute(
        """INSERT INTO admin_audit_log (admin_id, action, target_type, target_id, details)
           VALUES (%s, %s, %s, %s, %s)""",
        [admin_id, action, target_type, target_id, json.dumps(details or {}, ensure_ascii=False)],
    )
