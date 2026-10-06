# Исправление ошибки AttributeError в lesson_start.py

## Проблема

При запуске урока возникала ошибка:

```
AttributeError: 'str' object has no attribute 'get'
File "backend/app/services/lesson_start.py", line 190, in start_lesson
    gi = entry.get("group_index")
```

## Причина

LLM возвращает ответ в неожиданном формате. Ожидалось, что `generate_sentences()` вернёт `list[dict]`, но на самом деле:

1. `chat_json()` возвращает `dict` (извлечённый JSON из ответа LLM)
2. `generate_sentences()` должна извлечь список из этого dict
3. LLM может возвращать разные форматы:
   - Прямой список: `[{"group_index": 0, "sentence": "...", ...}, ...]`
   - Объект с полем "sentences": `{"sentences": [...]}`
   - Объект с полем "groups": `{"groups": [...]}`
   - Другой формат

## Решение

### 1. Добавлено логирование в `chat_json()`

**Файл:** `backend/app/services/llm/gigachat.py`

Добавлено логирование извлечённого JSON для отладки:

```python
# Извлекаем JSON
parsed_json = self._extract_json(content)

# Логируем извлечённый JSON
logger.info(f"📦 Extracted JSON type: {type(parsed_json)}")
logger.info(f"📦 Extracted JSON: {parsed_json}")
```

### 2. Исправлена обработка ответа в `generate_sentences()`

**Файл:** `backend/app/services/llm/helpers.py`

Добавлена интеллектуальная обработка ответа LLM:

```python
result = await llm_client.chat_json(...)

# Логируем результат для отладки
logger.info(f"📦 generate_sentences result type: {type(result)}")
logger.info(f"📦 generate_sentences result: {result}")

# Извлекаем список предложений из ответа LLM
if isinstance(result, list):
    return result
elif isinstance(result, dict):
    # Пробуем извлечь список из различных полей
    for key in ["sentences", "groups", "results", "exercises"]:
        if key in result and isinstance(result[key], list):
            logger.info(f"✅ Extracted list from field '{key}'")
            return result[key]
    
    # Если не нашли известное поле, возвращаем сам объект как единственный элемент
    logger.warning(f"⚠️ Could not extract list from dict, returning as single-item list")
    return [result]
else:
    logger.error(f"❌ Unexpected result type: {type(result)}")
    raise ValueError(f"Unexpected LLM response type: {type(result)}")
```

### 3. Добавлена проверка типа в `lesson_start.py`

**Файл:** `backend/app/services/lesson_start.py`

Добавлена проверка типа данных перед обработкой:

```python
# Логируем ответ от LLM для отладки
logger.info(f"📥 LLM Response type: {type(response)}")
logger.info(f"📥 LLM Response: {response}")

# Проверяем, что ответ - это список
if not isinstance(response, list):
    logger.error(f"❌ LLM returned non-list response: {type(response)}")
    logger.error(f"❌ Response content: {response}")
    raise LlmInvalidResponse("LLM response is not a list")

# Группируем ответ по group_index
response_by_index = {}
for entry in response:
    # Проверяем, что entry - это словарь
    if not isinstance(entry, dict):
        logger.warning(f"⚠️ Skipping non-dict entry: {entry}")
        continue
    
    gi = entry.get("group_index")
    if gi is not None:
        response_by_index[gi] = entry
```

## Как проверить работу

### 1. Перезапустите бэкенд

```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Запустите урок через фронтенд

В логах должны появиться подробные сообщения:

```
🔍 GigaChat API Request:
   URL: https://api.giga.chat/v1/chat/completions
   ...
📥 GigaChat API Response:
   Status: 200
   ...
📦 Extracted JSON type: <class 'dict'>
📦 Extracted JSON: {...}
📦 generate_sentences result type: <class 'dict'>
📦 generate_sentences result: {...}
✅ Extracted list from field 'sentences'
📥 LLM Response type: <class 'list'>
📥 LLM Response: [...]
```

### 3. Проверьте отсутствие ошибок

Не должно быть:
- ❌ `AttributeError: 'str' object has no attribute 'get'`
- ❌ `LLM returned non-list response`

## Ожидаемый формат ответа от LLM

LLM должен возвращать JSON в одном из следующих форматов:

### Вариант 1: Прямой список (предпочтительный)

```json
[
  {
    "group_index": 0,
    "sentence": "She runs every morning.",
    "reference_translation": "Она бегает каждое утро.",
    "target_words": [
      {
        "word_id": 1,
        "lemma": "run",
        "pos": "verb",
        "surface_form": "runs"
      }
    ]
  },
  {
    "group_index": 1,
    "sentence": "He reads books.",
    "reference_translation": "Он читает книги.",
    "target_words": [
      {
        "word_id": 2,
        "lemma": "read",
        "pos": "verb",
        "surface_form": "reads"
      }
    ]
  }
]
```

### Вариант 2: Объект с полем "sentences"

```json
{
  "sentences": [
    {
      "group_index": 0,
      "sentence": "She runs every morning.",
      "reference_translation": "Она бегает каждое утро.",
      "target_words": [...]
    }
  ]
}
```

### Вариант 3: Объект с полем "groups"

```json
{
  "groups": [
    {
      "group_index": 0,
      "sentence": "She runs every morning.",
      "reference_translation": "Она бегает каждое утро.",
      "target_words": [...]
    }
  ]
}
```

## Рекомендации по промпту

Если LLM возвращает неправильный формат, проверьте промпт в базе данных:

```sql
SELECT key, system_template FROM prompts WHERE key = 'generate_sentences';
```

Промпт должен явно указывать ожидаемый формат ответа. Пример:

```
Ты лингвист-методист. Для каждой группы слов составь предложение на английском языке.

ВАЖНО: Верни ответ СТРОГО в формате JSON-массива:
[
  {
    "group_index": 0,
    "sentence": "предложение на английском",
    "reference_translation": "перевод на русский",
    "target_words": [
      {
        "word_id": 1,
        "lemma": "слово",
        "pos": "часть_речи",
        "surface_form": "форма_слова_в_предложении"
      }
    ]
  }
]

Не добавляй никаких пояснений, только JSON.
```

## Статус

✅ **Добавлено логирование**  
✅ **Исправлена обработка ответа**  
✅ **Добавлена проверка типов**  
✅ **Проект успешно собирается**  
✅ **Готов к тестированию**

---

**Дата:** 2026-01-15  
**Версия:** 1.5.0
