# 🔍 Диагностика проблемы с генерацией предложений

## Проблема

LLM возвращает ответы с пустыми предложениями:
```
Group 0 validation failed: Group 0: sentence empty or too long (len=0)
```

## Добавленное логирование

Теперь в логах бэкенда будет полная информация:

### 1. Запрос к LLM (helpers.py)

```
================================================================================
📤 LLM REQUEST (generate_sentences)
================================================================================
Level: A2
Groups count: 4
Groups: [
  {
    "group_index": 0,
    "words": [
      {"lemma": "run", "pos": "verb"}
    ]
  },
  ...
]
Temperature: 0.7
Max tokens: 2048
System message length: 1234
System message (first 500 chars): Ты лингвист-методист...
User message: {
  "level": "A2",
  "groups": [...]
}
================================================================================
```

### 2. Сырой ответ от LLM (gigachat.py)

```
================================================================================
📥 LLM RAW RESPONSE
================================================================================
Finish reason: stop
Content length: 1567
Content (full):
[
  {
    "group_index": 0,
    "sentence": "She runs every morning.",
    "reference_translation": "Она бегает каждое утро.",
    "words": [
      {
        "word_id": 1,
        "lemma": "run",
        "pos": "verb",
        "surface_form": "runs"
      }
    ]
  }
]
================================================================================
```

### 3. Группы, отправляемые на генерацию (lesson_start.py)

```
================================================================================
📤 GENERATION ATTEMPT 1/3
================================================================================
Level: A2
Pending groups count: 4
Pending groups:
  Group 0: [{'lemma': 'run', 'pos': 'verb'}]
  Group 1: [{'lemma': 'book', 'pos': 'noun'}]
  ...
================================================================================
```

## Как диагностировать проблему

### Шаг 1: Перезапустите бэкенд

```bash
cd backend
uvicorn app.main:app --reload
```

### Шаг 2: Запустите урок через фронтенд

### Шаг 3: Проверьте логи бэкенда

Ищите следующие сообщения:

#### ✅ Если всё правильно:

```
📤 LLM REQUEST (generate_sentences)
...
📥 LLM RAW RESPONSE
Finish reason: stop
Content length: 1567
Content (full):
[
  {
    "group_index": 0,
    "sentence": "She runs every morning.",
    ...
  }
]
...
📦 Extracted JSON type: <class 'list'>
...
✅ Extracted list from field 'sentences'
```

#### ❌ Если sentence пустое:

```
📥 LLM RAW RESPONSE
Finish reason: stop
Content length: 123
Content (full):
[
  {
    "group_index": 0,
    "sentence": "",
    ...
  }
]
```

**Проблема:** LLM возвращает пустые предложения  
**Решение:** Проверить промпт в БД (см. ниже)

#### ❌ Если ответ не JSON:

```
📥 LLM RAW RESPONSE
Finish reason: stop
Content length: 456
Content (full):
Вот предложения для ваших слов:
1. She runs every morning.
2. He reads books.
```

**Проблема:** LLM не возвращает JSON  
**Решение:** Усилить промпт, добавить явное требование JSON

#### ❌ Если промпт отсутствует:

```
❌ prompt_missing: generate_sentences - using fallback
```

**Проблема:** Промпт не найден в БД  
**Решение:** Выполнить SQL скрипт (см. ниже)

## Проверка промпта в БД

### 1. Проверить текущий промпт

```bash
cd backend
psql $DATABASE_URL -f ../sql/check_prompts.sql
```

Или через pgAdmin:
```sql
SELECT key, system_template, LENGTH(system_template) as length 
FROM prompts 
WHERE key = 'generate_sentences';
```

### 2. Обновить промпт

Если промпт отсутствует или неправильный, выполните:

```bash
psql $DATABASE_URL -f ../sql/check_prompts.sql
```

Или через pgAdmin выполните содержимое файла `sql/check_prompts.sql`.

### 3. Проверить, что промпт обновился

```sql
SELECT key, LEFT(system_template, 100) as preview, LENGTH(system_template) as length 
FROM prompts 
WHERE key = 'generate_sentences';
```

Ожидаемый результат:
```
key                | preview                                        | length
-------------------|------------------------------------------------|--------
generate_sentences | Ты лингвист-методист и составляешь учебные п...| 1234
```

## Возможные причины проблемы

### Причина 1: Промпт отсутствует в БД

**Симптом:**
```
❌ prompt_missing: generate_sentences - using fallback
```

**Решение:**
```bash
psql $DATABASE_URL -f ../sql/check_prompts.sql
```

### Причина 2: Промпт неправильный

**Симптом:**
LLM возвращает текст вместо JSON или пустые предложения.

**Решение:**
Обновить промпт через SQL:
```sql
UPDATE prompts 
SET system_template = '...' -- см. sql/check_prompts.sql
WHERE key = 'generate_sentences';
```

### Причина 3: LLM не понимает формат

**Симптом:**
```
📥 LLM RAW RESPONSE
Content (full):
Вот предложения для ваших слов:
1. She runs every morning.
```

**Решение:**
Усилить промпт, добавить пример JSON и явное требование:
```
Верни СТРОГО JSON без пояснений и без markdown.
Не добавляй никаких текстовых пояснений.
```

### Причина 4: Модель не поддерживает JSON

**Симптом:**
LLM возвращает текст с markdown разметкой.

**Решение:**
Проверить модель в `.env`:
```env
GIGACHAT_MODEL=GigaChat
```

Или попробовать другую модель:
```env
GIGACHAT_MODEL=GigaChat-2-Max
```

### Причина 5: Температура слишком высокая

**Симптом:**
LLM возвращает непредсказуемые ответы.

**Решение:**
Уменьшить температуру в `.env`:
```env
GEN_TEMPERATURE=0.3
```

## Проверка после исправлений

1. Перезапустите бэкенд:
```bash
cd backend
uvicorn app.main:app --reload
```

2. Запустите урок через фронтенд

3. Проверьте логи:
```bash
# В логах должны появиться:
✅ Loaded prompt from DB: 1234 chars
📤 LLM REQUEST (generate_sentences)
📥 LLM RAW RESPONSE
📦 Extracted JSON type: <class 'list'>
```

4. Урок должен успешно создаться

## Дополнительные проверки

### Проверить, что слова есть в БД

```sql
SELECT COUNT(*) FROM words WHERE level = 'A2';
```

### Проверить, что профиль создан

```sql
SELECT * FROM learning_profiles WHERE user_id = YOUR_USER_ID;
```

### Проверить, что due-слова есть

```sql
SELECT * FROM user_words 
WHERE learning_profile_id = YOUR_PROFILE_ID 
  AND status = 'active' 
  AND due_lesson_number <= NEXT_LESSON_NUMBER;
```

## Статус

✅ Добавлено полное логирование запроса к LLM  
✅ Добавлено логирование сырого ответа от LLM  
✅ Добавлено логирование групп, отправляемых на генерацию  
✅ Создан SQL скрипт для проверки и обновления промпта  
✅ Создана документация по диагностике

---

**Версия:** 1.7.0  
**Дата:** 2026-01-15
