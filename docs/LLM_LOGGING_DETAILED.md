# 📊 Подробное логирование LLM

## Обзор

Добавлено максимально подробное логирование на всех этапах работы с LLM для диагностики проблем.

## Уровни логирования

### 1. `lesson_start.py` - Начало генерации

Логирует:
- Номер попытки (1/3, 2/3, 3/3)
- Уровень профиля
- Группы слов для генерации (полный JSON)
- Вызов `generate_sentences`
- Ответ от `generate_sentences`

**Пример:**
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
🚀 Calling generate_sentences...
   Level: A2
   Groups count: 4
   Groups: [
     {
       "group_index": 0,
       "words": [{"lemma": "run", "pos": "verb"}]
     },
     ...
   ]
✅ generate_sentences completed
   Response type: <class 'list'>
   Response: [
     {
       "group_index": 0,
       "sentence": "She runs every morning.",
       ...
     }
   ]
```

---

### 2. `helpers.py` - Подготовка запроса к LLM

Логирует:
- Загрузку промпта из БД (или fallback)
- Полный системный промпт
- Полное пользовательское сообщение
- Параметры запроса (temperature, max_tokens)

**Пример:**
```
✅ Loaded prompt from DB: 1234 chars
================================================================================
📤 LLM REQUEST (generate_sentences)
================================================================================
Level: A2
Groups count: 4
Groups: [
  {
    "group_index": 0,
    "words": [{"lemma": "run", "pos": "verb"}]
  },
  ...
]
Temperature: 0.7
Max tokens: 2048
System message length: 1234
--------------------------------------------------------------------------------
SYSTEM MESSAGE (FULL):
Ты лингвист-методист и составляешь учебные предложения.
Для КАЖДОЙ группы слов составь ровно одно короткое предложение...
--------------------------------------------------------------------------------
USER MESSAGE (FULL):
{
  "level": "A2",
  "groups": [
    {
      "group_index": 0,
      "words": [{"lemma": "run", "pos": "verb"}]
    },
    ...
  ]
}
================================================================================
```

---

### 3. `gigachat.py` - HTTP запрос к GigaChat API

Логирует:
- Полный HTTP запрос (URL, headers, payload)
- Полный HTTP ответ (status, headers, body)
- Извлечение JSON из ответа
- Ошибки парсинга JSON

**Пример:**
```
================================================================================
🔍 GigaChat HTTP REQUEST
================================================================================
URL: https://api.giga.chat/v1/chat/completions
Method: POST
--------------------------------------------------------------------------------
Headers:
  Authorization: Bearer eyJhbGciOi...
  Content-Type: application/json
  Accept: application/json
  User-Agent: 101slovo/1.0
--------------------------------------------------------------------------------
Payload:
{
  "model": "GigaChat",
  "messages": [
    {
      "role": "system",
      "content": "Ты лингвист-методист..."
    },
    {
      "role": "user",
      "content": "{\"level\": \"A2\", \"groups\": [...]}"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 2048
}
================================================================================

================================================================================
📥 GigaChat HTTP RESPONSE
================================================================================
Status: 200
--------------------------------------------------------------------------------
Response Headers:
  content-type: application/json
  x-request-id: abc123...
--------------------------------------------------------------------------------
Response Body (full):
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "[{\"group_index\": 0, \"sentence\": \"She runs every morning.\"...}]"
      },
      "finish_reason": "stop"
    }
  ],
  "created": 1234567890,
  "model": "GigaChat:2.0.28.2"
}
================================================================================
```

---

### 4. `gigachat.py` - Извлечение JSON

Логирует:
- Сырой ответ от LLM (content)
- Процесс извлечения JSON
- Результат извлечения

**Пример:**
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
🔍 Extracting JSON from content...
   Content starts with: [{"group_index": 0, "sentence": "She runs...
✅ JSON extracted successfully
================================================================================
📦 EXTRACTED JSON
================================================================================
Type: <class 'list'>
--------------------------------------------------------------------------------
Content (formatted):
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

---

### 5. `helpers.py` - Результат generate_sentences

Логирует:
- Тип результата
- Полный результат (отформатированный JSON)

**Пример:**
```
================================================================================
📦 generate_sentences RESULT
================================================================================
Result type: <class 'list'>
--------------------------------------------------------------------------------
Result (formatted):
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

---

### 6. `sentence_validation.py` - Валидация группы

Логирует:
- Входные данные валидации
- Тип и значение каждого поля
- Причины ошибок валидации

**Пример:**
```
================================================================================
🔍 VALIDATING GROUP 0
================================================================================
response_entry type: <class 'dict'>
response_entry keys: ['group_index', 'sentence', 'reference_translation', 'words']
--------------------------------------------------------------------------------
response_entry (full):
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
--------------------------------------------------------------------------------
Extracted fields:
   sentence: 'She runs every morning.' (type=str, len=24)
   reference_translation: 'Она бегает каждое утро.' (type=str, len=27)
   words: [{'word_id': 1, 'lemma': 'run', 'pos': 'verb', 'surface_form': 'runs'}] (type=list, len=1)
================================================================================
```

**Пример ошибки:**
```
================================================================================
🔍 VALIDATING GROUP 0
================================================================================
response_entry type: <class 'dict'>
response_entry keys: ['group_index', 'sentence', 'reference_translation', 'words']
--------------------------------------------------------------------------------
response_entry (full):
{
  "group_index": 0,
  "sentence": "",
  "reference_translation": "Она бегает каждое утро.",
  "words": []
}
--------------------------------------------------------------------------------
Extracted fields:
   sentence: '' (type=str, len=0)
   reference_translation: 'Она бегает каждое утро.' (type=str, len=27)
   words: [] (type=list, len=0)
================================================================================
❌ Validation failed: sentence empty or too long
   sentence value: ''
   sentence type: <class 'str'>
   sentence length: 0
```

---

## Диагностика проблем

### Проблема 1: sentence пустое

**Симптом в логах:**
```
Extracted fields:
   sentence: '' (type=str, len=0)
❌ Validation failed: sentence empty or too long
```

**Причины:**
1. LLM не генерирует предложение
2. Промпт неправильный
3. Модель не понимает задачу

**Решение:**
1. Проверить промпт в БД:
```sql
SELECT key, system_template FROM prompts WHERE key = 'generate_sentences';
```

2. Обновить промпт:
```bash
psql $DATABASE_URL -f sql/check_prompts.sql
```

3. Проверить логи HTTP запроса/ответа:
```
📤 LLM REQUEST (generate_sentences)
...
📥 LLM RAW RESPONSE
Content (full):
[ЗДЕСЬ БУДЕТ ОТВЕТ ОТ LLM]
```

---

### Проблема 2: LLM возвращает текст вместо JSON

**Симптом в логах:**
```
📥 LLM RAW RESPONSE
Content (full):
Вот предложения для ваших слов:
1. She runs every morning.
2. He reads books.
```

**Причина:**
LLM не понимает, что нужно вернуть JSON

**Решение:**
Усилить промпт:
```sql
UPDATE prompts 
SET system_template = '...Верни СТРОГО JSON без пояснений и без markdown. Не добавляй никаких текстовых пояснений...'
WHERE key = 'generate_sentences';
```

---

### Проблема 3: Ошибка парсинга JSON

**Симптом в логах:**
```
🔍 Extracting JSON from content...
   Content starts with: Вот предложения...
❌ Failed to extract JSON: No JSON found in response
   Content that failed: Вот предложения для ваших слов...
```

**Причина:**
LLM возвращает текст без JSON

**Решение:**
1. Проверить промпт
2. Попробовать другую модель: `GIGACHAT_MODEL=GigaChat-2-Max`
3. Уменьшить температуру: `GEN_TEMPERATURE=0.3`

---

### Проблема 4: Промпт отсутствует в БД

**Симптом в логах:**
```
❌ prompt_missing: generate_sentences - using fallback
```

**Решение:**
```bash
psql $DATABASE_URL -f sql/check_prompts.sql
```

---

## Как использовать логи

### 1. Перезапустите бэкенд

```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Запустите урок через фронтенд

### 3. Проверьте логи бэкенда

Ищите сообщения:
```
📤 GENERATION ATTEMPT 1/3
📤 LLM REQUEST (generate_sentences)
🔍 GigaChat HTTP REQUEST
📥 GigaChat HTTP RESPONSE
📥 LLM RAW RESPONSE
🔍 Extracting JSON from content...
📦 EXTRACTED JSON
📦 generate_sentences RESULT
🔍 VALIDATING GROUP 0
```

### 4. Проанализируйте логи

- Проверьте, что отправляется в LLM (промпт, группы)
- Проверьте, что возвращает LLM (сырой ответ)
- Проверьте, что извлекается JSON
- Проверьте, что проходит валидацию

---

## Статус

✅ Добавлено полное логирование запроса к LLM  
✅ Добавлено логирование HTTP запроса/ответа  
✅ Добавлено логирование извлечения JSON  
✅ Добавлено логирование валидации  
✅ Добавлено логирование ошибок с контекстом  
✅ Проект успешно собирается

---

**Версия:** 1.8.0  
**Дата:** 2026-01-15
