# 🔧 Исправление ошибки 422 Unprocessable Entity

## Дата
2026-01-15

## Проблема

При проверке упражнения возникала ошибка:
```
POST /lesson/evaluate HTTP/1.1" 422 Unprocessable Entity
```

## Диагностика

### Логи бэкенда

```
🔍 EVALUATE ENDPOINT CALLED
User ID: 1
Exercise ID: 1
User Translation: None  ← Проблема!
Don't Know: False

📝 Step 5: Validating input...
❌ User translation is empty
❌ ValueError: invalid_input
❌ Raising HTTP 422: invalid_input
```

### Анализ

Фронтенд отправлял `user_translation=None`, хотя пользователь вводил перевод.

## Причина

**Несоответствие имён полей между фронтендом и бэкендом:**

### Фронтенд (Lesson.tsx)
```typescript
body: JSON.stringify({
  exercise_id: currentExercise.exercise_id,
  translation: userTranslation,  // ❌ Неправильное имя!
  dont_know: false,
}),
```

### Бэкенд (lessons.py)
```python
class EvaluateRequest(BaseModel):
    exercise_id: int
    user_translation: Optional[str] = None  # ✅ Ожидает user_translation
    dont_know: bool = False
```

**Результат:** Бэкенд получал `user_translation=None`, потому что фронтенд отправлял поле `translation` вместо `user_translation`.

## Решение

### Исправлено в `src/pages/Lesson.tsx`

#### 1. Функция `handleSubmit` (строка 192)

**Было:**
```typescript
body: JSON.stringify({
  exercise_id: currentExercise.exercise_id,
  translation: userTranslation,  // ❌
  dont_know: false,
}),
```

**Стало:**
```typescript
body: JSON.stringify({
  exercise_id: currentExercise.exercise_id,
  user_translation: userTranslation,  // ✅
  dont_know: false,
}),
```

#### 2. Функция `handleDontKnow` (строка 233)

**Было:**
```typescript
body: JSON.stringify({
  exercise_id: currentExercise.exercise_id,
  translation: null,  // ❌
  dont_know: true,
}),
```

**Стало:**
```typescript
body: JSON.stringify({
  exercise_id: currentExercise.exercise_id,
  user_translation: null,  // ✅
  dont_know: true,
}),
```

## Проверка

### 1. Перезапустите фронтенд

```bash
npm run dev
```

### 2. Запустите урок через фронтенд

1. Откройте http://localhost:5173
2. Войдите в аккаунт
3. Начните урок
4. Введите перевод
5. Нажмите "Проверить"

### 3. Проверьте логи бэкенда

Должно быть:
```
🔍 EVALUATE ENDPOINT CALLED
User ID: 1
Exercise ID: 1
User Translation: Она бегает каждое утро.  ← Теперь не None!
Don't Know: False

📝 Step 5: Validating input...
Validating translation: 'Она бегает каждое утро.'
✅ Translation validated: 'Она бегает каждое утро.'

📝 Step 7: Calling LLM for evaluation...
✅ LLM evaluation completed

📝 Step 10: Forming response...
✅ Response formed:
  - Exercise ID: 1
  - Words count: 2
  - Lesson completed: False
```

## Статус

✅ Проблема диагностирована  
✅ Несоответствие имён полей найдено  
✅ Фронтенд исправлен (2 места)  
✅ Проект успешно собирается  
✅ Готов к тестированию

---

## Урок

**Всегда проверяйте соответствие имён полей между фронтендом и бэкендом!**

### Рекомендации

1. **Используйте TypeScript интерфейсы** для определения контракта API
2. **Создайте общие типы** для запросов и ответов
3. **Добавьте валидацию** на фронтенде перед отправкой
4. **Логируйте запросы** на фронтенде и бэкенде для отладки

### Пример общего типа

```typescript
// shared/types.ts
export interface EvaluateRequest {
  exercise_id: number;
  user_translation: string | null;
  dont_know: boolean;
}

// Lesson.tsx
const request: EvaluateRequest = {
  exercise_id: currentExercise.exercise_id,
  user_translation: userTranslation,
  dont_know: false,
};

const response = await fetch('http://localhost:8000/lesson/evaluate', {
  method: 'POST',
  headers: { ... },
  body: JSON.stringify(request),
});
```

---

**Версия:** 1.13.0  
**Дата:** 2026-01-15
