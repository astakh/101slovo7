"""
101slovo — Административные эндпоинты для просмотра БД.
Только чтение, маскирование чувствительных данных.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg import AsyncConnection, sql

from app.api.deps import get_current_admin_user_id, get_db

router = APIRouter()

# Таблицы, которые нельзя просматривать
EXCLUDED_TABLES = {"schema_migrations"}

# Чувствительные колонки (будут маскированы)
SENSITIVE_COLUMNS = {
    ("users", "password_hash"),
    ("refresh_tokens", "token_hash"),
}


@router.get("/db/tables")
async def list_tables(
    admin_id: int = Depends(get_current_admin_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Список таблиц с приблизительным числом строк.
    """
    cur = await db.execute(
        """SELECT table_name
           FROM information_schema.tables
           WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
           ORDER BY table_name"""
    )
    all_tables = [r["table_name"] for r in await cur.fetchall()]

    result = []
    for table in all_tables:
        if table in EXCLUDED_TABLES:
            continue

        # Приблизительное число строк
        cur = await db.execute(
            "SELECT reltuples::bigint as estimate FROM pg_class WHERE relname = %s",
            [table],
        )
        row = await cur.fetchone()
        row_count = max(row["estimate"], 0) if row else 0

        # Число колонок
        cur = await db.execute(
            """SELECT COUNT(*) as cnt FROM information_schema.columns
               WHERE table_name = %s AND table_schema = 'public'""",
            [table],
        )
        col_count = (await cur.fetchone())["cnt"]

        result.append(
            {
                "table_name": table,
                "row_count_estimate": row_count,
                "columns_count": col_count,
            }
        )

    return result


@router.get("/db/tables/{table_name}")
async def get_table_content(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    order_by: Optional[str] = None,
    order_dir: str = Query("asc", pattern="^(asc|desc)$"),
    search: Optional[str] = None,
    admin_id: int = Depends(get_current_admin_user_id),
    db: AsyncConnection = Depends(get_db),
):
    """
    Просмотр содержимого таблицы (только чтение).
    
    - Маскирует чувствительные колонки (password_hash, token_hash)
    - Поддерживает поиск по текстовым колонкам
    - Поддерживает сортировку и пагинацию
    """
    # 1. Валидация имени таблицы
    cur = await db.execute(
        """SELECT table_name FROM information_schema.tables
           WHERE table_schema = 'public' AND table_type = 'BASE TABLE' AND table_name = %s""",
        [table_name],
    )
    if not await cur.fetchone() or table_name in EXCLUDED_TABLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="table_not_found",
        )

    # 2. Получаем колонки
    cur = await db.execute(
        """SELECT column_name, data_type
           FROM information_schema.columns
           WHERE table_name = %s AND table_schema = 'public'
           ORDER BY ordinal_position""",
        [table_name],
    )
    columns = await cur.fetchall()

    # Первичный ключ
    cur = await db.execute(
        """SELECT kcu.column_name
           FROM information_schema.key_column_usage kcu
           JOIN information_schema.table_constraints tc
             ON kcu.constraint_name = tc.constraint_name AND kcu.table_schema = tc.table_schema
           WHERE kcu.table_name = %s AND tc.constraint_type = 'PRIMARY KEY'""",
        [table_name],
    )
    pk_columns = {r["column_name"] for r in await cur.fetchall()}

    # 3. Строим SELECT с маскированием
    select_parts = []
    for col in columns:
        col_name = col["column_name"]
        if (table_name, col_name) in SENSITIVE_COLUMNS:
            select_parts.append(
                sql.SQL("'••••••••' as {}").format(sql.Identifier(col_name))
            )
        else:
            select_parts.append(sql.Identifier(col_name))

    select_clause = sql.SQL(", ").join(select_parts)

    # 4. Базовый запрос
    query = sql.SQL("SELECT {} FROM {}").format(
        select_clause,
        sql.Identifier(table_name),
    )

    params = []

    # 5. Поиск
    text_columns = []
    conditions = []
    if search:
        text_columns = [
            c["column_name"]
            for c in columns
            if c["data_type"]
            in ("text", "character varying", "varchar", "char", "character")
            and (table_name, c["column_name"]) not in SENSITIVE_COLUMNS
        ]

        if text_columns:
            for tc in text_columns:
                conditions.append(
                    sql.SQL("{} ILIKE {}").format(
                        sql.Identifier(tc),
                        sql.Placeholder(),
                    )
                )
                params.append(f"%{search}%")

            if conditions:
                query += sql.SQL(" WHERE ") + sql.SQL(" OR ").join(conditions)

    # 6. Сортировка
    valid_columns = {c["column_name"] for c in columns}

    if order_by:
        if order_by not in valid_columns:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="invalid_order_by",
            )
        direction = sql.SQL("ASC") if order_dir == "asc" else sql.SQL("DESC")
        query += sql.SQL(" ORDER BY {} {}").format(
            sql.Identifier(order_by), direction
        )
    else:
        if pk_columns:
            pk_col = list(pk_columns)[0]
            query += sql.SQL(" ORDER BY {} ASC").format(sql.Identifier(pk_col))
        elif columns:
            query += sql.SQL(" ORDER BY {} ASC").format(
                sql.Identifier(columns[0]["column_name"])
            )

    # 7. Пагинация
    offset = (page - 1) * page_size
    query += sql.SQL(" LIMIT {} OFFSET {}").format(
        sql.Placeholder(),
        sql.Placeholder(),
    )
    params.extend([page_size, offset])

    cur = await db.execute(query, params)
    rows = await cur.fetchall()

    # 8. Общее число строк
    try:
        count_query = sql.SQL("SELECT COUNT(*) as cnt FROM {}").format(
            sql.Identifier(table_name)
        )
        if search and text_columns and conditions:
            count_query += sql.SQL(" WHERE ") + sql.SQL(" OR ").join(conditions)

        cur = await db.execute(
            count_query, params[: len(params) - 2]
        )  # Без LIMIT/OFFSET
        total = (await cur.fetchone())["cnt"]
    except Exception:
        total = None

    # 9. Метаданные колонок
    column_metadata = []
    for col in columns:
        col_name = col["column_name"]
        column_metadata.append(
            {
                "name": col_name,
                "type": col["data_type"],
                "is_primary_key": col_name in pk_columns,
                "masked": (table_name, col_name) in SENSITIVE_COLUMNS,
            }
        )

    return {
        "table_name": table_name,
        "columns": column_metadata,
        "rows": rows,
        "page": page,
        "page_size": page_size,
        "total": total,
    }
