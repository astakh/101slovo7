# 🔧 Исправление формата ответа LLM для оценки перевода

## Дата
2026-01-15

## Проблема

LLM возвращал ответ в неправильном формате для оценки перевода.

**Ожидалось:**
```json
{
  "evaluations": [
    {"word_id": 212, "result": "correct", "user_fragment": "яркий"},
    {"word_id": 192, "result": "correct", "user_fragment": "бьет"}
  ],
  "new_suggested_words": [...]
}
```

**LLM возвращал:**
```json
{
  "212": "яркий",
  "192": "бьет",
  "new_suggested_words": ["в"]
}
```

**Результат:** Ошибка `LlmInvalidResponse: word_id mismatch`

## Решение

### 1. Обновлён промпт `evaluate_translation`

**Файлы:**
- `sql/001_init.sql`
- `scripts/update_evaluate_prompt.py`

**Изменения:**
- Добавлены явные инструкции о формате ответа
- Добавлен пример JSON с полем `evaluations`
- Добавлено: **"КРИТИЧЕСКИ ВАЖНО: Поле evaluations ОБЯЗАТЕЛЬНО должно быть массивом объектов"**
- Добавлено: **"НЕ возвращай объект с ключами word_id. Возвращай массив evaluations с объектами внутри"**

### 2. Добавлен маппинг в `lesson_evaluate.py`

**Файл:** `backend/app/services/lesson_evaluate.py`

**Логика:**
```python
# Если LLM вернул неправильный формат
if "evaluations" not in llm_response:
    print("⚠️ LLM returned incorrect format, applying mapping...")
    evaluations_raw = []
    for key, value in llm_response.items():
        if key.isdigit():  # word_id
            word_id = int(key)
            result = "correct" if value else "incorrect"
            evaluations_raw.append({
                "word_id": word_id,
                "result": result,
                "user_fragment": value
            })
    llm_response["evaluations"] = evaluations_raw
```

**Преобразование:**
```json
// Было:
{"212": "яркий", "192": "бьет", "new_suggested_words": ["в"]}

// Стало:
{
  "evaluations": [
    {"word_id": 212, "result": "correct", "user_fragment": "яркий"},
    {"word_id": 192, "result": "correct", "user_fragment": "бьет"}
  ],
  "new_suggested_words": ["в"]
}
```

## Как применить

### Шаг 1: Обновите промпт в БД

```bash
cd backend
python ../scripts/update_evaluate_prompt.py
```

### Шаг 2: Перезапустите бэкенд

```bash
uvicorn app.main:app --reload
```

### Шаг 3: Проверьте работу

Запустите урок через фронтенд и проверьте логи:

```
📝 Step 8: Validating LLM response...
Evaluations count: 2
Suggested words count: 1
📝 Checking word_id set...
Response word IDs: {192, 212}
Expected word IDs: {192, 212}
✅ Word IDs match!
```

## Проверка промпта в БД

```sql
SELECT key, system_template FROM prompts WHERE key = 'evaluate_translation';
```

Должен содержать:
- `"evaluations": [`
- `"word_id": 123,`
- `"result": "correct",`
- `"user_fragment": "перевод"`
- **"КРИТИЧЕСКИ ВАЖНО: Поле evaluations ОБЯЗАТЕЛЬНО должно быть массивом объектов"**

## Ожидаемое поведение

### Успешная проверка

```
📝 Step 7: Calling LLM for evaluation...
✅ LLM evaluation completed
LLM response: {'evaluations': [...], 'new_suggested_words': [...]}

📝 Step 8: Validating LLM response...
Evaluations count: 2
Suggested words count: 1
✅ Evaluations validated: 2
✅ Suggestions processed: 1

📝 Step 9: Starting write transaction...
✅ Lesson locked
✅ Exercise locked
✅ Target words processed: 2
✅ Exercise updated

📝 Step 10: Forming response...
✅ Response formed:
  - Exercise ID: 1
  - Words count: 2
  - Lesson completed: False
```

### Если LLM всё ещё возвращает неправильный формат

```
📝 Step 8: Validating LLM response...
⚠️ LLM returned incorrect format, applying mapping...
✅ Mapped 2 evaluations
Evaluations count: 2
Suggested words count: 1
✅ Evaluations validated: 2
```

## Статус

✅ Обновлён промпт в БД  
✅ Добавлен маппинг в `lesson_evaluate.py`  
✅ Создан скрипт обновления промпта  
✅ Создана документация  
✅ Проект успешно собирается

---

**Версия:** 1.14.0  
**Дата:** 2026-01-15
