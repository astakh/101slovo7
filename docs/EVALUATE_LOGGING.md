# 🔍 Логирование проверки упражнения

## Обзор

Добавлено подробное логирование в эндпоинт `POST /lesson/evaluate` и сервис `evaluate_exercise` для диагностики ошибок 422 Unprocessable Entity.

## Уровни логирования

### 1. Эндпоинт `lesson_evaluate` (lessons.py)

Логирует:
- Входные данные запроса (exercise_id, user_translation, dont_know)
- Профиль пользователя
- Вызов `evaluate_exercise`
- Ошибки с полным traceback

**Пример:**
```
================================================================================
🔍 EVALUATE ENDPOINT CALLED
================================================================================
User ID: 1
Request: exercise_id=1 user_translation='Она бегает каждое утро.' dont_know=False
Exercise ID: 1
User Translation: Она бегает каждое утро.
Don't Know: False
================================================================================
📊 Profile: {'id': 1}
🚀 Calling evaluate_exercise...
```

### 2. Сервис `evaluate_exercise` (lesson_evaluate.py)

Логирует все 10 этапов алгоритма 5.5:

#### Этап 1: Доступ и состояние
```
📝 Step 1: Getting exercise data...
Exercise found: True
  - Status: pending
  - Lesson ID: 1
  - Profile ID: 1
```

#### Этап 2: Идемпотентность
```
📝 Step 2: Checking idempotency...
```

#### Этап 3: Порядок упражнений
```
📝 Step 3: Checking exercise order...
First pending exercise ID: 1
Current exercise ID: 1
```

#### Этап 4: Статус урока
```
📝 Step 4: Checking lesson status...
Lesson status: in_progress
```

#### Этап 5: Валидация ввода
```
📝 Step 5: Validating input...
Validating translation: 'Она бегает каждое утро.'
✅ Translation validated: 'Она бегает каждое утро.'
```

#### Этап 6: Ветка "Не знаю"
```
📝 Step 6: Don't know branch: False
✅ Using LLM evaluation branch
```

#### Этап 7: Вызов LLM
```
📝 Step 7: Calling LLM for evaluation...
LLM target words prepared: 2
✅ LLM evaluation completed
LLM response: {...}
```

#### Этап 8: Валидация ответа LLM
```
📝 Step 8: Validating LLM response...
Evaluations count: 2
Suggested words count: 1
📝 Checking word_id set...
Response word IDs: {1, 2}
Expected word IDs: {1, 2}
📝 Checking for duplicates...
📝 Validating results...
✅ Evaluations validated: 2
📝 Processing suggestions...
✅ Suggestions processed: 1
```

#### Этап 9: Транзакция записи
```
📝 Step 9: Starting write transaction...
Lesson number: 1
📝 Locking lesson...
✅ Lesson locked
📝 Locking exercise...
✅ Exercise locked
📝 Processing target words...
  Processing word ID: 1
    Evaluation: correct
    Applying SRS: stage=0, result=correct
    SRS result: new_stage=1, due=2, status=active
  Processing word ID: 2
    Evaluation: correct
    Applying SRS: stage=0, result=correct
    SRS result: new_stage=1, due=2, status=active
✅ Target words processed: 2
📝 Forming suggested_words JSONB...
📝 Updating exercise...
✅ Exercise updated
📝 Checking lesson completion...
Pending exercises: 0
✅ All exercises completed, marking lesson as completed
✅ Lesson completed at 2026-01-15
📝 Recording exercise_evaluated event...
✅ Event recorded
```

#### Этап 10: Формирование ответа
```
📝 Step 10: Forming response...
✅ Response formed:
  - Exercise ID: 1
  - Words count: 2
  - Suggestions count: 1
  - Lesson completed: True
================================================================================
```

## Диагностика ошибок

### Ошибка 422 Unprocessable Entity

**Возможные причины:**

1. **Неправильный формат запроса**
   ```
   🔍 EVALUATE ENDPOINT CALLED
   Exercise ID: None  ← Отсутствует
   ```
   **Решение:** Проверить, что фронтенд отправляет `exercise_id`

2. **Пустой перевод**
   ```
   📝 Step 5: Validating input...
   ❌ User translation is empty
   ```
   **Решение:** Проверить, что пользователь ввёл перевод

3. **Ошибка валидации перевода**
   ```
   📝 Step 5: Validating input...
   Validating translation: '...'
   ❌ Translation validation failed: ...
   ```
   **Решение:** Проверить, что перевод соответствует требованиям (длина, символы)

4. **Упражнение не найдено**
   ```
   📝 Step 1: Getting exercise data...
   Exercise found: False
   ❌ Exercise not found
   ```
   **Решение:** Проверить, что exercise_id корректный

5. **Не текущее упражнение**
   ```
   📝 Step 3: Checking exercise order...
   First pending exercise ID: 2
   Current exercise ID: 1
   ❌ Not the current exercise
   ```
   **Решение:** Пользователь пытается оценить не текущее упражнение

6. **Урок не активен**
   ```
   📝 Step 4: Checking lesson status...
   Lesson status: completed
   ❌ Lesson not active
   ```
   **Решение:** Урок уже завершён

7. **Ошибка LLM**
   ```
   📝 Step 7: Calling LLM for evaluation...
   ❌ LLM evaluation failed: ...
   ```
   **Решение:** Проверить логи GigaChat API

8. **Несоответствие word_id**
   ```
   📝 Step 8: Validating LLM response...
   Response word IDs: {1, 3}
   Expected word IDs: {1, 2}
   ❌ Word ID mismatch!
   ```
   **Решение:** LLM вернул неправильные word_id

## Как использовать

### 1. Перезапустите бэкенд

```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Запустите урок через фронтенд

### 3. Нажмите "Проверить"

### 4. Проверьте логи бэкенда

Ищите сообщения:
```
🔍 EVALUATE ENDPOINT CALLED
📝 Step 1: Getting exercise data...
📝 Step 2: Checking idempotency...
...
✅ Response formed:
```

### 5. Найдите ошибку

Если возникла ошибка 422, ищите сообщение с ❌:
```
❌ User translation is empty
❌ Exercise not found
❌ Not the current exercise
❌ Lesson not active
❌ Translation validation failed: ...
```

## Примеры успешного выполнения

### Пример 1: Обычная проверка

```
🔍 EVALUATE ENDPOINT CALLED
User ID: 1
Exercise ID: 1
User Translation: Она бегает каждое утро.
Don't Know: False

📝 Step 1: Getting exercise data...
Exercise found: True
  - Status: pending
  - Lesson ID: 1

📝 Step 5: Validating input...
✅ Translation validated: 'Она бегает каждое утро.'

📝 Step 7: Calling LLM for evaluation...
✅ LLM evaluation completed

📝 Step 8: Validating LLM response...
✅ Evaluations validated: 2

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

### Пример 2: Завершение урока

```
📝 Step 9: Starting write transaction...
📝 Checking lesson completion...
Pending exercises: 0
✅ All exercises completed, marking lesson as completed
✅ Lesson completed at 2026-01-15

📝 Step 10: Forming response...
✅ Response formed:
  - Exercise ID: 5
  - Words count: 3
  - Lesson completed: True  ← Урок завершён!
```

### Пример 3: Ветка "Не знаю"

```
🔍 EVALUATE ENDPOINT CALLED
Don't Know: True

📝 Step 6: Don't know branch: True
✅ Using 'don't know' branch

📝 Step 9: Starting write transaction...
✅ Exercise updated
```

## Статус

✅ Добавлено полное логирование эндпоинта  
✅ Добавлено логирование всех 10 этапов алгоритма  
✅ Добавлена обработка ошибок с traceback  
✅ Создана документация по диагностике

---

**Версия:** 1.12.0  
**Дата:** 2026-01-15
