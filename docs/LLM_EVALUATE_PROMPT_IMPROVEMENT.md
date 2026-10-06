# 🐛 Исправление проблемы: LLM пропускает целевые слова

## Дата
2026-01-15

## Проблема

LLM возвращала оценку только для части целевых слов, что приводило к ошибке:

```
❌ Word ID mismatch!
Response word IDs: {192, 233}
Expected word IDs: {192, 233, 178}
```

**Пример:**
- Упражнение содержит 3 целевых слова: `bite`, `carpet`, `battle`
- LLM оценила только 2 слова: `bite` и `carpet`
- Слово `battle` было пропущено
- Система выбрасывала ошибку `word_id mismatch`

## Причина

Промпт не требовал от LLM **обязательно** оценить ВСЕ целевые слова. LLM могла:
- Пропустить некоторые слова
- Оценить только часть слов
- Сосредоточиться на "более важных" словах

Это приводило к нестабильной работе системы.

## Решение

### 1. Усилен промпт `evaluate_translation`

**Файлы:**
- `sql/001_init.sql` (строка 201)
- `scripts/update_evaluate_prompt.py`

**Добавлены инструкции:**

```
ЗАДАЧА: оцени перевод ВСЕХ целевых слов из `target_words`. 
Ты ДОЛЖЕН вернуть оценку для КАЖДОГО слова из списка `target_words`.

КРИТИЧЕСКИ ВАЖНО:
- Ты ДОЛЖЕН оценить ВСЕ слова из `target_words`, ни одно не пропусти
- Количество объектов в `evaluations` ДОЛЖНО быть равно количеству слов в `target_words`
- Каждое слово из `target_words` ДОЛЖНО иметь свой объект в `evaluations` 
  с соответствующим `word_id`

ПРОВЕРЬ СЕБЯ:
- Все ли слова из `target_words` оценены?
- Количество `evaluations` равно количеству `target_words`?
- Каждый `word_id` из `target_words` присутствует в `evaluations`?
```

**Изменения:**
- ✅ Добавлено требование оценить ВСЕ слова
- ✅ Добавлена проверка количества
- ✅ Добавлен чек-лист для самопроверки
- ✅ Добавлен пример с несколькими словами

### 2. Добавлен fallback в коде

**Файл:** `backend/app/services/lesson_evaluate.py` (строки 250-260)

**Было:**
```python
if response_word_ids != expected_word_ids:
    print(f"❌ Word ID mismatch!")
    raise LlmInvalidResponse("word_id mismatch")
```

**Стало:**
```python
# Fallback: если LLM пропустила слова, дополним их как incorrect
missing_word_ids = expected_word_ids - response_word_ids
if missing_word_ids:
    print(f"⚠️ LLM missed {len(missing_word_ids)} words, adding as incorrect")
    for word_id in missing_word_ids:
        evaluations_raw.append({
            "word_id": word_id,
            "result": "incorrect",
            "user_fragment": None
        })
    print(f"✅ Added missing words as incorrect")
```

**Логика:**
- Если LLM пропустила слова, система автоматически добавляет их как `incorrect`
- Это предотвращает ошибку и позволяет уроку продолжиться
- Пользователь видит, что пропущенные слова помечены как неправильные

## Как это работает

### Сценарий 1: LLM оценила все слова (идеальный случай)

```
Target words: [192, 233, 178]
LLM response: {
  "evaluations": [
    {"word_id": 192, "result": "correct", ...},
    {"word_id": 233, "result": "correct", ...},
    {"word_id": 178, "result": "incorrect", ...}
  ]
}

✅ Все слова оценены, продолжаем работу
```

### Сценарий 2: LLM пропустила слово (fallback)

```
Target words: [192, 233, 178]
LLM response: {
  "evaluations": [
    {"word_id": 192, "result": "correct", ...},
    {"word_id": 233, "result": "correct", ...}
    // Слово 178 пропущено!
  ]
}

⚠️ LLM missed 1 words, adding as incorrect
✅ Added missing words as incorrect

Final evaluations: [
  {"word_id": 192, "result": "correct", ...},
  {"word_id": 233, "result": "correct", ...},
  {"word_id": 178, "result": "incorrect", "user_fragment": null}  // Добавлено автоматически
]
```

## Как применить

### Шаг 1: Обновите промпт в БД

```bash
cd backend
python ../scripts/update_evaluate_prompt.py
```

**Или** выполните SQL вручную:

```bash
psql $DATABASE_URL -f ../sql/001_init.sql
```

### Шаг 2: Перезапустите бэкенд

```bash
uvicorn app.main:app --reload
```

### Шаг 3: Проверьте работу

1. Запустите урок
2. Введите перевод
3. Нажмите "Проверить"
4. Проверьте логи:

**Ожидаемые логи:**
```
📝 Step 8: Validating LLM response...
Evaluations count: 3
Suggested words count: 1
📝 Checking word_id set...
Response word IDs: {192, 233, 178}
Expected word IDs: {192, 233, 178}
✅ All words evaluated
```

**Или если LLM пропустила слово:**
```
📝 Step 8: Validating LLM response...
Evaluations count: 2
Suggested words count: 1
📝 Checking word_id set...
Response word IDs: {192, 233}
Expected word IDs: {192, 233, 178}
⚠️ LLM missed 1 words, adding as incorrect
✅ Added missing words as incorrect
```

## Преимущества решения

### 1. Надежность
- ✅ Система работает даже если LLM пропускает слова
- ✅ Нет критических ошибок
- ✅ Урок продолжается

### 2. Прозрачность
- ✅ Пользователь видит, какие слова пропущены
- ✅ Пропущенные слова помечаются как incorrect
- ✅ Логирование показывает, что произошло

### 3. Гибкость
- ✅ Промпт усилен, но не слишком строгий
- ✅ Fallback срабатывает только при необходимости
- ✅ Система адаптируется к поведению LLM

## Проверка промпта

### Проверьте текущий промпт в БД

```sql
SELECT key, system_template FROM prompts WHERE key = 'evaluate_translation';
```

Должен содержать:
- "оцени перевод ВСЕХ целевых слов"
- "Ты ДОЛЖЕН вернуть оценку для КАЖДОГО слова"
- "Количество объектов в `evaluations` ДОЛЖНО быть равно количеству слов"
- "ПРОВЕРЬ СЕБЯ: Все ли слова из `target_words` оценены?"

### Проверьте логи

После проверки упражнения в логах должно быть:
```
✅ LLM evaluation completed
LLM response: {'evaluations': [...], 'new_suggested_words': [...]}
📝 Step 8: Validating LLM response...
Evaluations count: 3  // Должно быть равно количеству target_words
```

## Статус

✅ Обновлён промпт `evaluate_translation`  
✅ Добавлен fallback в `lesson_evaluate.py`  
✅ Обновлён SQL скрипт  
✅ Обновлён Python скрипт  
✅ Проект успешно собирается  
✅ Готово к тестированию

---

## Связанные файлы

- `scripts/update_evaluate_prompt.py` - скрипт обновления промпта
- `sql/001_init.sql` - SQL миграция с промптом
- `backend/app/services/lesson_evaluate.py` - сервис оценки упражнения
- `docs/LLM_EVALUATE_PROMPT_IMPROVEMENT.md` - этот документ

---

**Версия:** 1.19.0  
**Дата:** 2026-01-15
