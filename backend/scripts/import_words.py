"""
101slovo — Импорт слов из JSON-файла в БД.

Использование (из папки backend/):
    python scripts/import_words.py ../data/it.json
    python scripts/import_words.py ../data/it.json --dry-run
    python scripts/import_words.py ../data/it.json --admin-id 1
"""

import argparse
import asyncio
import sys
from pathlib import Path

# ═══════════════════════════════════════════
# ИСПРАВЛЕНИЕ: на Windows нужен SelectorEventLoop для psycopg3
# ═══════════════════════════════════════════
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Добавляем путь к app для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.pool import close_pool, init_pool, get_pool
from app.services.dictionary_import import import_dictionary


async def main():
    parser = argparse.ArgumentParser(description="Импорт слов из JSON в БД")
    parser.add_argument("json_path", help="Путь к JSON файлу")
    parser.add_argument("--dry-run", action="store_true", help="Только проверка, без записи")
    parser.add_argument("--admin-id", type=int, help="ID пользователя для логирования (по умолчанию первый в БД)")
    args = parser.parse_args()

    json_path = Path(args.json_path)

    if not json_path.exists():
        print(f"❌ Файл не найден: {json_path}")
        sys.exit(1)

    print("=" * 60)
    print(f"📥 Импорт слов из: {json_path}")
    print(f"   Dry run: {args.dry_run}")
    print("=" * 60)

    # Читаем файл
    file_content = json_path.read_bytes()
    print(f"📄 Размер файла: {len(file_content)} байт")

    # Инициализируем пул БД
    await init_pool()
    try:
        pool = get_pool()
        async with pool.connection() as db:
            # ─────────────────────────────────────────────
            # Определяем admin_id для логирования
            # ─────────────────────────────────────────────
            admin_id = args.admin_id
            if not admin_id:
                # Ищем первого пользователя в БД
                cur = await db.execute("SELECT id, email FROM users ORDER BY id LIMIT 1")
                row = await cur.fetchone()
                if not row:
                    print("❌ В базе нет пользователей. Зарегистрируйтесь через приложение, чтобы создался пользователь.")
                    return
                admin_id = row["id"]
                print(f"ℹ️  Действие будет записано на пользователя: {row['email']} (ID: {admin_id})")
            else:
                print(f"ℹ️  Используется указанный admin_id: {admin_id}")

            async with db.transaction():
                result = await import_dictionary(db, admin_id, file_content, args.dry_run)
    finally:
        await close_pool()

    # Вывод результата
    print("\n" + "=" * 60)
    if result["dry_run"]:
        print("🔍 РЕЗУЛЬТАТ DRY RUN (запись не производилась):")
        print("   (В dry-run режиме added/updated/skipped всегда 0,")
        print("    смотрите на список errors — если он пуст, файл корректен)")
    else:
        print("✅ РЕЗУЛЬТАТ ИМПОРТА:")

    print(f"   Словарь: {result['dictionary']['code']} — {result['dictionary']['name']}")
    print(f"   ➕ Добавлено:  {result['added']}")
    print(f"   🔄 Обновлено:  {result['updated']}")
    print(f"   ⏭️  Пропущено: {result['skipped']}")

    if result["errors"]:
        print(f"\n   ❌ Ошибки валидации ({len(result['errors'])}):")
        for err in result["errors"][:10]:
            print(f"      - {err}")
        if len(result["errors"]) > 10:
            print(f"      ... и ещё {len(result['errors']) - 10}")
    else:
        print("   ✅ Ошибок валидации нет.")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())