# 🔍 Добавлено подробное логирование ответа LLM

## Дата
2026-01-15

## Проблема

При запуске урока все группы валидации не проходят с ошибкой:
```
Group 0 validation failed: Group 0: sentence empty or too long
Group 1 validation failed: Group 1: sentence empty or too long
Group 2 validation failed: Group 2: sentence empty or too long
Group 3 validation failed: Group 3: sentence empty or too long
```

Это означает, что LLM возвращает ответ, но поля `sentence` либо отсутствуют, либо пусты.

## Решение

Добавлено подробное логирование на всех этапах обработки ответа LLM.

---

## Изменённые файлы

### 1. `backend/app/services/lesson_start.py`

Добавлено логирование полного ответа LLM с деталями каждого entry:

```python
# Логируем ответ от LLM для отладки
logger.info(f"📥 LLM Response type: {type(response)}")
logger.info(f"📥 LLM Response (full): {response}")

if isinstance(response, list):
    logger.info(f"📥 LLM Response length: {len(response)}")
    for idx, entry in enumerate(response):
        logger.info(f"📥 Entry {idx}: {entry}")
        if isinstance(entry, dict):
            logger.info(f"   - Keys: {list(entry.keys())}")
            logger.info(f"   - sentence: '{entry.get('sentence', 'MISSING')}'")
            logger.info(f"   - reference_translation: '{entry.get('reference_translation', 'MISSING')}'")
            logger.info(f"   - group_index: {entry.get('group_index', 'MISSING')}")

# При обработке каждой группы
logger.info(f"🔍 Processing entry with group_index={gi}")
```

### 2. `backend/app/utils/sentence_validation.py`

Добавлено логирование входных данных валидации:

```python
# Логируем входные данные для отладки
logger.info(f"🔍 Validating group {group_index}")
logger.info(f"   response_entry keys: {list(response_entry.keys()) if isinstance(response_entry, dict) else 'NOT A DICT'}")
logger.info(f"   response_entry: {response_entry}")

logger.info(f"   sentence: '{sentence}' (len={len(sentence)})")
logger.info(f"   reference_translation: '{reference_translation}' (len={len(reference_translation)})")
logger.info(f"   words: {words}")

# При ошибке валидации
logger.error(f"   ❌ Validation failed: sentence empty or too long (len={len(sentence)})")
```

---

## Как проверить работу

### 1. Перезапустите бэкенд

```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Запустите урок через фронтенд

### 3. Проверьте логи бэкенда

Теперь в логах вы увидите полную информацию о том, что возвращает LLM:

```
📥 LLM Response type: <class 'list'>
📥 LLM Response (full): [...]
📥 LLM Response length: 4
📥 Entry 0: {...}
   - Keys: ['group_index', 'sentence', 'reference_translation', 'words']
   - sentence: 'She runs every morning.'
   - reference_translation: 'Она бегает каждое утро.'
   - group_index: 0
📥 Entry 1: {...}
   - Keys: ['group_index', 'sentence', 'reference_translation', 'words']
   - sentence: 'He reads books.'
   - reference_translation: 'Он читает книги.'
   - group_index: 1
...

🔍 Validating group 0
   response_entry keys: ['group_index', 'sentence', 'reference_translation', 'words']
   response_entry: {...}
   sentence: 'She runs every morning.' (len=24)
   reference_translation: 'Она бегает каждое утро.' (len=27)
   words: [...]
```

### 4. Анализ логов

#### Если sentence пустое:
```
📥 Entry 0: {...}
   - sentence: ''
   - reference_translation: 'Она бегает каждое утро.'
```
**Проблема:** LLM не генерирует предложение  
**Решение:** Проверить промпт в БД или изменить модель

#### Если sentence отсутствует:
```
📥 Entry 0: {...}
   - Keys: ['group_index', 'translation', 'words']
   - sentence: 'MISSING'
```
**Проблема:** LLM возвращает неправильное имя поля  
**Решение:** Исправить промпт или добавить маппинг полей

#### Если ответ не список:
```
📥 LLM Response type: <class 'dict'>
❌ LLM returned non-list response: <class 'dict'>
```
**Проблема:** LLM возвращает объект вместо списка  
**Решение:** Проверить промпт или добавить извлечение списка из объекта

---

## Ожидаемый формат ответа от LLM

LLM должен возвращать JSON в следующем формате:

```json
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
  },
  {
    "group_index": 1,
    "sentence": "He reads books.",
    "reference_translation": "Он читает книги.",
    "words": [
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

---

## Возможные проблемы и решения

### Проблема 1: LLM возвращает строку вместо JSON

**Симптом:**
```
📥 LLM Response type: <class 'str'>
```

**Решение:** Проверить промпт в БД:
```sql
SELECT key, system_template FROM prompts WHERE key = 'generate_sentences';
```

Убедитесь, что промпт явно требует JSON:
```
Верни ответ СТРОГО в формате JSON-массива. Не добавляй никаких пояснений, только JSON.
```

### Проблема 2: LLM возвращает объект вместо списка

**Симптом:**
```
📥 LLM Response type: <class 'dict'>
📥 Entry 0: {...}
   - Keys: ['sentences']
```

**Решение:** Код уже обрабатывает этот случай в `helpers.py`:
```python
for key in ["sentences", "groups", "results", "exercises"]:
    if key in result and isinstance(result[key], list):
        return result[key]
```

### Проблема 3: Поля имеют неправильные имена

**Симптом:**
```
📥 Entry 0: {...}
   - Keys: ['group_index', 'text', 'translation', 'words']
   - sentence: 'MISSING'
```

**Решение:** Добавить маппинг полей в `lesson_start.py`:
```python
# Маппинг возможных имён полей
field_mapping = {
    'text': 'sentence',
    'translation': 'reference_translation',
}

for entry in response:
    for old_key, new_key in field_mapping.items():
        if old_key in entry and new_key not in entry:
            entry[new_key] = entry[old_key]
```

### Проблема 4: LLM возвращает пустые предложения

**Симптом:**
```
📥 Entry 0: {...}
   - sentence: ''
```

**Решение:** 
1. Проверить промпт в БД
2. Увеличить `max_tokens` в запросе
3. Попробовать другую модель

---

## Проверка промпта в БД

```sql
-- Проверить текущий промпт
SELECT key, system_template FROM prompts WHERE key = 'generate_sentences';

-- Обновить промпт (пример)
UPDATE prompts 
SET system_template = 'Ты лингвист-методист. Для каждой группы слов составь предложение на английском языке уровня {level}.

ВАЖНО: Верни ответ СТРОГО в формате JSON-массива:
[
  {
    "group_index": 0,
    "sentence": "предложение на английском",
    "reference_translation": "перевод на русский",
    "words": [
      {
        "word_id": 1,
        "lemma": "слово",
        "pos": "часть_речи",
        "surface_form": "форма_слова_в_предложении"
      }
    ]
  }
]

Не добавляй никаких пояснений, только JSON.'
WHERE key = 'generate_sentences';
```

---

## Статус

✅ **Добавлено подробное логирование**  
✅ **Логируются все этапы обработки**  
✅ **Проект успешно собирается**  
✅ **Готов к диагностике**

---

## Следующие шаги

1. Перезапустить бэкенд
2. Запустить урок через фронтенд
3. Проанализировать логи
4. Определить проблему по логам
5. Применить соответствующее решение

---

**Версия:** 1.6.0  
**Дата:** 2026-01-15
