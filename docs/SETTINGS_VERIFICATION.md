# Проверка сохранения настроек в БД

## Дата проверки
2026-01-15

## Статус
✅ **Все настройки корректно сохраняются в БД**

---

## Проверенные функции

### 1. Онбординг (`POST /onboarding/complete`)

**Что сохраняется:**
- ✅ `users.timezone` — часовой пояс пользователя
- ✅ `users.is_onboarded` — флаг завершения онбординга (true)
- ✅ `learning_profiles.level` — уровень английского (A1/A2/B1/B2)
- ✅ `learning_profiles.dictionary_id` — ID выбранного словаря
- ✅ `learning_profiles.daily_lesson_limit` — дневной лимит уроков (по умолчанию 1)
- ✅ `learning_profiles.words_per_lesson` — слов на урок (по умолчанию 5)
- ✅ `events` — событие `onboarding_completed`

**Найденная проблема:**
❌ **Исправлено:** Раньше использовался `DEFAULT_DICTIONARY_CODE` вместо выбранного пользователем словаря.

**Что было исправлено:**
1. Добавлено поле `dictionary_id` в `OnboardingRequest` (backend/app/schemas/onboarding.py)
2. Изменена логика в `complete_onboarding()` — теперь используется `req.dictionary_id` вместо `settings.DEFAULT_DICTIONARY_CODE`
3. Добавлена проверка существования выбранного словаря
4. Обновлён фронтенд — `Onboarding.tsx` теперь отправляет `dictionary_id`

**SQL запросы:**
```sql
-- Обновление пользователя
UPDATE users 
SET timezone = %s, is_onboarded = true, updated_at = now() 
WHERE id = %s

-- Создание профиля обучения
INSERT INTO learning_profiles 
(user_id, level, dictionary_id, daily_lesson_limit, words_per_lesson) 
VALUES (%s, %s, %s, %s, %s)

-- Логирование события
INSERT INTO events (user_id, type, payload) 
VALUES (%s, 'onboarding_completed', %s)
```

**Транзакция:**
✅ Все операции выполняются в одной транзакции (`async with db.transaction()`)

---

### 2. Обновление профиля обучения (`PATCH /learning-profile`)

**Что можно изменить:**
- ✅ `level` — уровень английского
- ✅ `dictionary_id` — словарь
- ✅ `daily_lesson_limit` — дневной лимит уроков
- ✅ `words_per_lesson` — слов на урок

**Что сохраняется:**
- ✅ `learning_profiles.level`
- ✅ `learning_profiles.dictionary_id`
- ✅ `learning_profiles.daily_lesson_limit`
- ✅ `learning_profiles.words_per_lesson`
- ✅ `learning_profiles.updated_at`

**Валидация:**
- ✅ Проверка существования словаря
- ✅ Проверка лимитов (daily_lesson_limit <= DAILY_LESSON_LIMIT_MAX)
- ✅ Проверка диапазона (WORDS_PER_LESSON_MIN <= words_per_lesson <= WORDS_PER_LESSON_MAX)

**SQL запрос:**
```sql
UPDATE learning_profiles 
SET level = %s, dictionary_id = %s, daily_lesson_limit = %s, 
    words_per_lesson = %s, updated_at = now() 
WHERE id = %s
```

**Транзакция:**
✅ Используется `FOR UPDATE` для блокировки строки

---

### 3. Смена часового пояса (`PATCH /settings/timezone`)

**Что сохраняется:**
- ✅ `users.timezone` — новый часовой пояс
- ✅ `users.timezone_changed_at` — дата последнего изменения
- ✅ `users.updated_at` — дата обновления

**Валидация:**
- ✅ Проверка валидности IANA timezone
- ✅ Идемпотентность (если тот же пояс — просто возвращаем данные)
- ✅ Лимит 7 дней между изменениями

**SQL запрос:**
```sql
UPDATE users 
SET timezone = %s, timezone_changed_at = now(), updated_at = now() 
WHERE id = %s
```

**Транзакция:**
✅ Используется `FOR UPDATE` для блокировки строки

---

## Проверка целостности данных

### Связи между таблицами

```
users
  ├── learning_profiles (1:1)
  │     ├── dictionary_id → dictionaries.id
  │     └── user_words (1:N)
  │           └── word_id → words.id
  ├── lessons (1:N)
  │     └── lesson_exercises (1:N)
  └── events (1:N)
```

### Проверено:
- ✅ `learning_profiles.user_id` — UNIQUE (один профиль на пользователя)
- ✅ `learning_profiles.dictionary_id` — FOREIGN KEY → dictionaries.id
- ✅ `users.timezone` — проверяется через `zoneinfo.available_timezones()`
- ✅ `users.is_onboarded` — CHECK (is_onboarded = false OR timezone IS NOT NULL)

---

## Тестовые сценарии

### Сценарий 1: Полный онбординг

**Действия:**
1. Регистрация пользователя
2. Онбординг с параметрами:
   - level: "A2"
   - dictionary_id: 2 (business)
   - timezone: "Europe/Moscow"

**Ожидаемый результат в БД:**
```sql
-- users
SELECT id, email, timezone, is_onboarded FROM users WHERE id = 1;
-- Результат:
-- id | email          | timezone        | is_onboarded
-- 1  | test@test.com  | Europe/Moscow   | true

-- learning_profiles
SELECT id, user_id, level, dictionary_id, daily_lesson_limit, words_per_lesson 
FROM learning_profiles WHERE user_id = 1;
-- Результат:
-- id | user_id | level | dictionary_id | daily_lesson_limit | words_per_lesson
-- 1  | 1       | A2    | 2             | 1                  | 5

-- events
SELECT type, payload FROM events WHERE user_id = 1;
-- Результат:
-- type                  | payload
-- onboarding_completed  | {"level": "A2", "timezone": "Europe/Moscow"}
```

### Сценарий 2: Изменение настроек

**Действия:**
1. PATCH /learning-profile с `{ "level": "B1", "words_per_lesson": 10 }`

**Ожидаемый результат:**
```sql
SELECT level, words_per_lesson, updated_at FROM learning_profiles WHERE user_id = 1;
-- level | words_per_lesson | updated_at
-- B1    | 10               | 2026-01-15 12:00:00
```

### Сценарий 3: Смена часового пояса

**Действия:**
1. PATCH /settings/timezone с `{ "timezone": "Asia/Yekaterinburg" }`

**Ожидаемый результат:**
```sql
SELECT timezone, timezone_changed_at FROM users WHERE id = 1;
-- timezone          | timezone_changed_at
-- Asia/Yekaterinburg| 2026-01-15 12:00:00
```

---

## Проблемы и решения

### Проблема 1: Словарь не сохранялся
**Симптом:** При онбординге всегда использовался словарь "general", независимо от выбора пользователя.

**Причина:** В `onboarding.py` использовался `settings.DEFAULT_DICTIONARY_CODE` вместо `req.dictionary_id`.

**Решение:**
1. Добавлено поле `dictionary_id` в `OnboardingRequest`
2. Изменена логика в `complete_onboarding()` — используется `req.dictionary_id`
3. Добавлена проверка существования словаря
4. Обновлён фронтенд для отправки `dictionary_id`

**Файлы изменены:**
- `backend/app/schemas/onboarding.py` — добавлено поле `dictionary_id`
- `backend/app/api/v1/onboarding.py` — изменена логика сохранения
- `src/pages/Onboarding.tsx` — обновлён API вызов

---

## Рекомендации

### Для разработки

1. **Всегда проверяйте сохранение данных в БД** после изменения API
2. **Используйте транзакции** для атомарности операций
3. **Добавляйте валидацию** на уровне БД (CHECK constraints)
4. **Логируйте важные события** в таблицу `events`

### Для тестирования

1. **Проверяйте БД напрямую** через SQL запросы
2. **Тестируйте edge cases:**
   - Пустые значения
   - Некорректные данные
   - Повторные вызовы
3. **Проверяйте транзакции:**
   - Откат при ошибке
   - Блокировки (FOR UPDATE)

### Для production

1. **Добавьте мониторинг** таблицы `events`
2. **Настройте алерты** на ошибки валидации
3. **Регулярно проверяйте** целостность данных
4. **Делайте бэкапы** БД перед миграциями

---

## Вывод

✅ **Все настройки корректно сохраняются в БД**

Исправлена критическая проблема с сохранением выбранного словаря при онбординге. Теперь пользователь может выбрать любой словарь из списка, и он будет корректно сохранён в `learning_profiles.dictionary_id`.

Все операции выполняются в транзакциях с правильной блокировкой строк. Валидация данных работает на всех уровнях (фронтенд, API, БД).
