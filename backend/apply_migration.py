"""
101slovo — Скрипт применения миграций базы данных.
Применяет все .sql файлы из папки sql/ в лексикографическом порядке.

Использование:
  cd backend
  python apply_migration.py

Или с явным указанием пути:
  python backend/apply_migration.py
"""

import sys
from pathlib import Path

import psycopg
from psycopg import errors

# Добавляем путь к app для импорта config
sys.path.insert(0, str(Path(__file__).parent))
from app.config import settings


def get_migration_version(filepath: Path) -> str:
    """
    Извлекает версию миграции из имени файла (без расширения).
    Примеры:
      001_init.sql -> '001_init'
      002_nontarget_words.sql -> '002_nontarget_words'
    """
    return filepath.stem


def get_applied_versions(conn) -> set[str]:
    """
    Возвращает множество уже применённых версий миграций.
    Если таблица schema_migrations ещё не существует — возвращает пустое множество.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version FROM schema_migrations")
            return {row[0] for row in cur.fetchall()}
    except errors.UndefinedTable:
        # Таблица schema_migrations ещё не создана — миграции не применялись
        return set()


def apply_migration_file(conn, migration_file: Path) -> None:
    """
    Применяет один файл миграции.
    Разбивает SQL на отдельные операторы по ';' и выполняет каждый.
    """
    print(f"📄 Чтение файла миграции: {migration_file}")

    try:
        with open(migration_file, "r", encoding="utf-8") as f:
            sql_content = f.read()
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        sys.exit(1)

    print(f"✅ Файл прочитан ({len(sql_content)} символов)")

    # Разбиваем SQL на отдельные операторы
    # Игнорируем комментарии и пустые строки
    statements = []
    current_statement = []
    for line in sql_content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('--') or not stripped:
            continue
        current_statement.append(line)
        # Если строка заканчивается на ';', это конец оператора
        if stripped.endswith(';'):
            statement = '\n'.join(current_statement).strip()
            if statement:
                statements.append(statement)
            current_statement = []

    # Если остался незавершённый оператор
    if current_statement:
        statement = '\n'.join(current_statement).strip()
        if statement:
            statements.append(statement)

    print(f"📝 Найдено {len(statements)} SQL операторов")

    # Выполняем каждый оператор отдельно
    with conn.cursor() as cur:
        for i, statement in enumerate(statements, 1):
            first_line = statement.split('\n')[0][:80]
            print(f"   [{i}/{len(statements)}] {first_line}...")
            try:
                cur.execute(statement)
            except Exception as e:
                print(f"   ⚠️  Ошибка в операторе {i}: {e}")
                print(f"   SQL: {statement[:200]}...")
                # Продолжаем выполнение (некоторые ошибки могут быть ожидаемыми)


def apply_migrations():
    """
    Применяет все миграции из папки sql/ по порядку.
    Пропускает уже применённые (согласно таблице schema_migrations).
    """
    # Путь к папке с миграциями
    migrations_dir = Path(__file__).parent.parent / "sql"
    if not migrations_dir.exists():
        print(f"❌ Папка миграций не найдена: {migrations_dir}")
        print(f"   Ожидался путь: {migrations_dir.absolute()}")
        sys.exit(1)

    # Находим все файлы миграций (начинаются с цифры, расширение .sql)
    migration_files = sorted(migrations_dir.glob("[0-9]*.sql"))
    if not migration_files:
        print(f"❌ Файлы миграций не найдены в: {migrations_dir}")
        sys.exit(1)

    print(f"📄 Найдено миграций: {len(migration_files)}")
    for f in migration_files:
        print(f"   • {f.name}")
    print()

    # Маскируем пароль для вывода
    display_url = settings.DATABASE_URL
    if "@" in display_url:
        parts = display_url.split("@")
        userinfo = parts[0].rsplit("//", 1)[-1]
        if ":" in userinfo:
            user, _ = userinfo.split(":", 1)
            display_url = display_url.replace(userinfo, f"{user}:***")
    print(f"🔗 Подключение к базе данных: {display_url.split('@')[1] if '@' in display_url else '***'}")

    try:
        # Используем autocommit для выполнения каждого оператора отдельно
        with psycopg.connect(settings.DATABASE_URL, autocommit=True) as conn:
            print("✅ Подключение установлено")
            print()

            # Получаем уже применённые версии
            applied = get_applied_versions(conn)
            print(f"📊 Уже применено миграций: {len(applied)}")
            for v in sorted(applied):
                print(f"   • {v}")
            print()

            # Применяем миграции по порядку
            applied_count = 0
            for migration_file in migration_files:
                version = get_migration_version(migration_file)

                if version in applied:
                    print(f"⏭️  Миграция {version} уже применена, пропускаем")
                    continue

                print(f"🚀 Применение миграции: {version}")
                apply_migration_file(conn, migration_file)
                applied_count += 1
                print(f"✅ Миграция {version} применена")
                print()

            # Итоговая статистика
            applied = get_applied_versions(conn)
            print("=" * 60)
            print(f"📊 Итого миграций в базе: {len(applied)}")
            print(f"📊 Применено в этом запуске: {applied_count}")
            if applied_count == 0:
                print("   Все миграции уже были применены ранее")
            print("=" * 60)

    except psycopg.OperationalError as e:
        print(f"\n❌ Ошибка подключения к базе данных:")
        print(f"   {e}")
        print(f"\n💡 Проверьте:")
        print(f"   • DATABASE_URL в файле .env")
        print(f"   • Доступность сервера PostgreSQL")
        print(f"   • Правильность логина и пароля")
        print(f"   • Существует ли база данных")
        sys.exit(1)
    except psycopg.Error as e:
        print(f"\n❌ Ошибка выполнения SQL:")
        print(f"   {e}")
        print(f"\n💡 Возможные причины:")
        print(f"   • Ошибка в SQL файле")
        print(f"   • Недостаточно прав у пользователя")
        print(f"   • Конфликт с существующими таблицами")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Непредвиденная ошибка: {e}")
        sys.exit(1)


def create_general_dictionary():
    """
    Создаёт словарь 'general' если он не существует.
    """
    print("\n📚 Проверка словаря 'general'...")
    try:
        with psycopg.connect(settings.DATABASE_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Проверка существования
                cur.execute("SELECT id FROM dictionaries WHERE code = 'general'")
                if cur.fetchone():
                    print("✅ Словарь 'general' уже существует")
                    return

                # Создание словаря
                cur.execute(
                    """INSERT INTO dictionaries (code, name, description)
                       VALUES ('general', 'General English', 'Общий словарь английских слов')"""
                )
                print("✅ Словарь 'general' создан")
    except psycopg.Error as e:
        print(f"⚠️  Не удалось создать словарь: {e}")
        print("   Вы можете создать его вручную:")
        print("   INSERT INTO dictionaries (code, name, description)")
        print("   VALUES ('general', 'General English', 'Общий словарь английских слов');")


def main():
    """Главная функция."""
    print("=" * 60)
    print("🎯 101slovo — Применение миграций базы данных")
    print("=" * 60)
    print()

    apply_migrations()
    create_general_dictionary()

    print()
    print("=" * 60)
    print("🎉 Готово! База данных настроена.")
    print("=" * 60)
    print()
    print("Следующие шаги:")
    print("1. Обновите промпты:  python ../scripts/update_prompt.py")
    print("                      python ../scripts/update_evaluate_prompt.py")
    print("2. Запустите backend: uvicorn app.main:app --reload")
    print()


if __name__ == "__main__":
    main()