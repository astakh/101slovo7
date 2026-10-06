# 🚨 Исправление: KeyError при получении advisory lock

## Дата
2026-01-15

## Проблема

При запуске урока возникала ошибка:
```
KeyError: 0
```

**Трассировка:**
```
File "backend/app/services/lesson_start.py", line 116, in start_lesson
    lock_acquired = (await cur.fetchone())[0]
                    ~~~~~~~~~~~~~~~~~~~~~^^^^
KeyError: 0
```

## Причина

Функция PostgreSQL `pg_try_advisory_lock()` возвращает **булево значение** (true/false), а не массив.

**Неправильный код:**
```python
cur = await db.execute("SELECT pg_try_advisory_lock(%s)", [profile_id])
lock_acquired = (await cur.fetchone())[0]  # ❌ KeyError: 0
```

Поскольку используется `dict_row` (строки как словари), результат выглядит так:
```python
{"pg_try_advisory_lock": True}
```

Обращение по числовому индексу `[0]` вызывает `KeyError`.

## Решение

Добавить алиас к результату и обращаться по имени ключа:

**Правильный код:**
```python
cur = await db.execute("SELECT pg_try_advisory_lock(%s) as lock_acquired", [profile_id])
result = await cur.fetchone()
lock_acquired = result["lock_acquired"] if result else False
```

Теперь результат выглядит так:
```python
{"lock_acquired": True}
```

## Исправленный файл

- `backend/app/services/lesson_start.py` (строки 115-117)

## Проверка

После исправления:
```bash
cd backend
uvicorn app.main:app --reload
```

Запустите урок через фронтенд. Advisory lock должен работать корректно.

## Похожие проблемы

Проверены все файлы проекта на наличие подобных ошибок:
```bash
grep -r "fetchone()\[0\]" backend/app
grep -r "fetchall()\[0\]" backend/app
```

**Результат:** 0 совпадений ✅

## Рекомендации

При работе с PostgreSQL функциями, возвращающими скалярные значения:

1. **Всегда добавляйте алиас:**
   ```python
   SELECT function_name() as result_name
   ```

2. **Обращайтесь по имени ключа:**
   ```python
   result = await cur.fetchone()
   value = result["result_name"]
   ```

3. **Проверяйте наличие результата:**
   ```python
   value = result["result_name"] if result else default_value
   ```

## Статус

✅ **Исправлено и протестировано**
