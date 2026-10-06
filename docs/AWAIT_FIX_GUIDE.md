# 🚨 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Отсутствие await в бэкенде

## Проблема

Во всех файлах бэкенда отсутствует `await` перед вызовами `cur.fetchone()` и `cur.fetchall()`.

**Симптомы:**
```
TypeError: 'coroutine' object is not subscriptable
RuntimeWarning: coroutine 'AsyncCursor.fetchone' was never awaited
```

**Причина:**
В psycopg 3 async все методы cursor являются асинхронными и требуют `await`.

## Решение

### Автоматическое исправление

Запустите скрипт:

```bash
cd backend
python ../fix_await.py
```

Скрипт автоматически добавит `await` перед всеми вызовами `cur.fetchone()` и `cur.fetchall()`.

### Ручное исправление

Если скрипт не работает, исправьте вручную следующие файлы:

#### 1. `app/api/v1/dashboard.py` (5 мест)

**Строка 51:**
```python
# Было:
row = cur.fetchone()

# Стало:
row = await cur.fetchone()
```

**Строка 74:**
```python
# Было:
lessons_today = cur.fetchone()["cnt"]

# Стало:
lessons_today = (await cur.fetchone())["cnt"]
```

**Строка 87:**
```python
# Было:
resume_row = cur.fetchone()

# Стало:
resume_row = await cur.fetchone()
```

**Строка 105:**
```python
# Было:
words_dict = {r["status"]: r["cnt"] for r in cur.fetchall()}

# Стало:
words_dict = {r["status"]: r["cnt"] for r in await cur.fetchall()}
```

**Строка 121:**
```python
# Было:
dates = {r["completed_local_date"] for r in cur.fetchall()}

# Стало:
dates = {r["completed_local_date"] for r in await cur.fetchall()}
```

#### 2. `app/api/v1/profile.py` (6 мест)

Аналогично добавьте `await` перед всеми `cur.fetchone()` и `cur.fetchall()`.

#### 3. `app/api/v1/settings.py` (15 мест)

Аналогично добавьте `await` перед всеми `cur.fetchone()` и `cur.fetchall()`.

#### 4. `app/api/v1/vocabulary.py` (3 места)

Аналогично добавьте `await` перед всеми `cur.fetchone()`.

#### 5. `app/api/v1/lessons.py` (12 мест)

Аналогично добавьте `await` перед всеми `cur.fetchone()`.

#### 6. `app/api/v1/admin.py` (7 мест)

Аналогично добавьте `await` перед всеми `cur.fetchone()` и `cur.fetchall()`.

#### 7. `app/api/v1/admin_db.py` (9 мест)

Аналогично добавьте `await` перед всеми `cur.fetchone()` и `cur.fetchall()`.

#### 8. `app/api/v1/admin_prompts.py` (3 места)

Аналогично добавьте `await` перед всеми `cur.fetchone()` и `cur.fetchall()`.

#### 9. `app/services/lesson_preview.py` (7 мест)

Аналогично добавьте `await` перед всеми `cur.fetchone()` и `cur.fetchall()`.

#### 10. `app/services/lesson_evaluate.py` (13 мест)

Аналогично добавьте `await` перед всеми `cur.fetchone()` и `cur.fetchall()`.

#### 11. `app/services/lesson_start.py` (16 мест)

Аналогично добавьте `await` перед всеми `cur.fetchone()` и `cur.fetchall()`.

#### 12. `app/services/dictionary_import.py` (3 места)

Аналогично добавьте `await` перед всеми `cur.fetchone()`.

#### 13. `app/services/llm/helpers.py` (2 места)

Аналогично добавьте `await` перед всеми `cur.fetchone()`.

## Проверка

После исправления запустите бэкенд:

```bash
cd backend
uvicorn app.main:app --reload
```

Если нет ошибок `RuntimeWarning: coroutine ... was never awaited`, значит всё исправлено.

## Почему это важно

Без `await` вызовы `fetchone()` и `fetchall()` возвращают coroutine объекты вместо реальных данных. Это приводит к:

1. **TypeError** при попытке обратиться к полям (`user["password_hash"]`)
2. **Некорректной работе** всех эндпоинтов
3. **Невозможности** регистрации, входа, создания уроков

## Список исправленных файлов

✅ `app/api/v1/auth.py` — исправлено
✅ `app/api/v1/onboarding.py` — исправлено
✅ `app/api/deps.py` — исправлено
✅ `app/services/lesson_summary.py` — исправлено
✅ `app/services/lesson_resume.py` — исправлено

⏳ Остальные файлы требуют исправления (см. выше)

## Быстрое исправление всех файлов

Если хотите исправить все файлы сразу, используйте команду:

```bash
cd backend
find app -name "*.py" -exec sed -i 's/\([^t]\)cur\.fetchone()/\1await cur.fetchone()/g' {} \;
find app -name "*.py" -exec sed -i 's/\([^t]\)cur\.fetchall()/\1await cur.fetchall()/g' {} \;
```

**Внимание:** Эта команда может сломать строки, где уже есть `await`. Проверьте результат вручную.

## Альтернативный способ

Используйте Python скрипт `fix_await.py` в корне проекта:

```bash
python fix_await.py
```

Скрипт безопасно исправит все файлы, пропуская строки с уже существующим `await`.
