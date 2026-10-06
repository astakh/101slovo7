# 🐛 Исправление ошибки в settings.py

## Дата
2026-01-15

## Проблема

При запросе `GET /learning-profile` возникала ошибка:

```
TypeError: 'coroutine' object is not subscriptable
RuntimeWarning: coroutine 'AsyncCursor.fetchone' was never awaited
```

**Место ошибки:** `backend/app/api/v1/settings.py`, строки 84-86

## Причина

Отсутствовал `await` перед вызовом `.fetchone()`:

```python
# БЫЛО (неправильно):
user_tz = (
    await db.execute("SELECT timezone FROM users WHERE id = %s", [user_id])
).fetchone()["timezone"]  # ❌ Нет await перед fetchone()
```

`db.execute()` возвращает курсор, а `fetchone()` - это асинхронный метод, который требует `await`.

## Решение

Добавлен `await` перед `.fetchone()`:

```python
# СТАЛО (правильно):
cur = await db.execute("SELECT timezone FROM users WHERE id = %s", [user_id])
user_tz = (await cur.fetchone())["timezone"]  # ✅ Есть await
```

## Исправленный код

**Файл:** `backend/app/api/v1/settings.py`

**Строки 83-87:**

```python
# Точность за 30 дней
cur = await db.execute("SELECT timezone FROM users WHERE id = %s", [user_id])
user_tz = (await cur.fetchone())["timezone"]
today = get_user_today(user_tz)
```

## Проверка всего файла

Проверены все вызовы `.fetchone()` и `.fetchall()` в файле `settings.py`:

✅ Строка 41: `row = await cur.fetchone()`
✅ Строка 58: `words_dict = {r["status"]: r["cnt"] for r in await cur.fetchall()}`
✅ Строка 66: `completed_lessons = (await cur.fetchone())["cnt"]`
✅ Строка 78: `acc_row = await cur.fetchone()`
✅ Строка 85: `user_tz = (await cur.fetchone())["timezone"]` ← **ИСПРАВЛЕНО**
✅ Строка 97: `acc30_row = await cur.fetchone()`
✅ Строка 149: `profile = await cur.fetchone()`
✅ Строка 170: `if not await cur.fetchone():`
✅ Строка 223: `rows = await cur.fetchall()`
✅ Строка 266: `user = await cur.fetchone()`
✅ Строка 283: `profile_id = (await cur.fetchone())["id"]`
✅ Строка 291: `lessons_today = (await cur.fetchone())["cnt"]`
✅ Строка 299: `dates = {r["completed_local_date"] for r in await cur.fetchall()}`
✅ Строка 340: `profile_id = (await cur.fetchone())["id"]`
✅ Строка 348: `lessons_today = (await cur.fetchone())["cnt"]`
✅ Строка 356: `dates = {r["completed_local_date"] for r in await cur.fetchall()}`

**Все 16 вызовов имеют `await`!** ✅

## Как проверить

### 1. Перезапустите бэкенд
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Откройте страницу настроек
1. Войдите в аккаунт
2. Перейдите на Dashboard
3. Нажмите кнопку "Настройки" (⚙️)

### 3. Проверьте логи бэкенда
Должно быть:
```
INFO:     127.0.0.1:xxxxx - "GET /learning-profile HTTP/1.1" 200 OK
```

**НЕ должно быть:**
```
RuntimeWarning: coroutine 'AsyncCursor.fetchone' was never awaited
TypeError: 'coroutine' object is not subscriptable
```

### 4. Проверьте отображение данных
Должны отображаться реальные данные из БД:
- ✅ Ваш уровень
- ✅ Ваши лимиты
- ✅ Ваш словарь
- ✅ Ваш часовой пояс
- ✅ Ваша статистика

## Статус

✅ Исправлена ошибка в `settings.py`  
✅ Проверены все вызовы `.fetchone()` и `.fetchall()`  
✅ Проект успешно собирается  
✅ Готово к тестированию

---

## Связанные файлы

- `backend/app/api/v1/settings.py` - исправленный файл
- `docs/SETTINGS_FIX.md` - документация по настройкам
- `docs/ASYNC_AWAIT_FIX.md` - этот документ

---

**Версия:** 1.21.0  
**Дата:** 2026-01-15
