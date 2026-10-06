# 🐛 Исправление ошибки "Cannot read properties of undefined (reading 'sentence')"

## Дата
2026-01-15

## Проблема

При загрузке существующего урока через `GET /lesson/{id}/current` возникала ошибка на фронтенде:

```
Uncaught TypeError: Cannot read properties of undefined (reading 'sentence')
    at Lesson (Lesson.tsx:382:36)
```

## Причина

Было две проблемы:

### 1. Неправильная логика индексации на фронтенде

**Файл:** `src/pages/Lesson.tsx` (строки 107-114)

**Было:**
```typescript
setLesson({
  lesson_id: data.lesson_id,
  lesson_number: data.lesson_number || lessonNumber || 1,
  exercises_total: data.exercises_total,
  exercises: [data.current_exercise], // Массив из ОДНОГО элемента
});

setCurrentExerciseIndex(data.exercises_done || 0); // Может быть > 0!
```

**Проблема:**
- Массив `exercises` содержит только ОДИН элемент (индекс 0)
- Но `currentExerciseIndex` устанавливается из `exercises_done`, который может быть > 0
- Например, если `exercises_done = 1`, то `currentExerciseIndex = 1`
- При обращении к `lesson.exercises[1]` получаем `undefined`
- При обращении к `undefined.sentence` получаем ошибку

### 2. Бэкенд не возвращал все необходимые поля

**Файл:** `backend/app/services/lesson_resume.py` (строки 43-65)

**Было:**
```python
cur = await db.execute(
    """SELECT id, order_index, target_sentence 
       FROM lesson_exercises ...""",
)

return {
    "current_exercise": {
        "exercise_id": current["id"],
        "order_index": current["order_index"],
        "sentence": current["target_sentence"],
    },
}
```

**Проблема:**
- Не возвращались поля `reference_translation` и `target_words`
- Фронтенд ожидал эти поля для отображения упражнения

## Решение

### 1. Исправлена логика индексации на фронтенде

**Файл:** `src/pages/Lesson.tsx`

**Стало:**
```typescript
const data = await response.json();

console.log('📥 API response for /lesson/current:', data);

// Проверяем, что current_exercise существует
if (!data.current_exercise) {
  throw new Error('Текущее упражнение не найдено в ответе API');
}

// Преобразуем данные из API в формат Lesson
setLesson({
  lesson_id: data.lesson_id,
  lesson_number: data.lesson_number || lessonNumber || 1,
  exercises_total: data.exercises_total,
  exercises: [data.current_exercise], // Массив из ОДНОГО элемента
});

// Всегда начинаем с индекса 0, так как массив содержит только одно упражнение
setCurrentExerciseIndex(0);
```

**Изменения:**
- Добавлена проверка на существование `current_exercise`
- `currentExerciseIndex` всегда устанавливается в 0
- Добавлено логирование для отладки

### 2. Бэкенд теперь возвращает все необходимые поля

**Файл:** `backend/app/services/lesson_resume.py`

**Стало:**
```python
cur = await db.execute(
    """SELECT id, order_index, target_sentence, reference_translation, target_words
       FROM lesson_exercises ...""",
)

return {
    "current_exercise": {
        "exercise_id": current["id"],
        "order_index": current["order_index"],
        "sentence": current["target_sentence"],
        "reference_translation": current["reference_translation"],
        "target_words": current["target_words"],
    },
}
```

**Изменения:**
- Добавлены поля `reference_translation` и `target_words` в SELECT запрос
- Добавлены эти поля в возвращаемый объект `current_exercise`

### 3. Добавлена защита от undefined на фронтенде

**Файл:** `src/pages/Lesson.tsx` (строки 336-360)

**Добавлено:**
```typescript
const currentExercise = lesson.exercises[currentExerciseIndex];

// Логирование для отладки
console.log('🔍 Lesson data:', lesson);
console.log('🔍 Current exercise index:', currentExerciseIndex);
console.log('🔍 Current exercise:', currentExercise);

if (!currentExercise) {
  console.error('❌ Current exercise is undefined!');
  console.error('   lesson.exercises:', lesson.exercises);
  console.error('   currentExerciseIndex:', currentExerciseIndex);
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 max-w-md text-center">
        <AlertCircle className="text-red-500 mx-auto mb-4" size={48} />
        <h2 className="text-xl font-bold text-gray-900 mb-2">Ошибка</h2>
        <p className="text-gray-600 mb-6">Не удалось загрузить упражнение</p>
        <button
          onClick={() => navigate('/dashboard')}
          className="px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700"
        >
          На главную
        </button>
      </div>
    </div>
  );
}
```

**Изменения:**
- Добавлено логирование для отладки
- Добавлена проверка на undefined
- Добавлено отображение ошибки пользователю с кнопкой "На главную"

## Как проверить

### 1. Перезапустите бэкенд
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Перезапустите фронтенд
```bash
npm run dev
```

### 3. Проверьте загрузку существующего урока
1. Создайте новый урок
2. Перейдите на страницу урока
3. Обновите страницу (F5)
4. Убедитесь, что урок загружается без ошибок
5. Проверьте консоль браузера (F12) - должны быть логи:
   ```
   📥 API response for /lesson/current: {...}
   🔍 Lesson data: {...}
   🔍 Current exercise index: 0
   🔍 Current exercise: {...}
   ```

### 4. Проверьте отображение упражнения
- Должно отображаться предложение
- Должны отображаться целевые слова
- Должно отображаться поле для ввода перевода

## Ожидаемое поведение

### До исправления
```
❌ Uncaught TypeError: Cannot read properties of undefined (reading 'sentence')
```

### После исправления
```
✅ Упражнение успешно загружается
✅ Отображается предложение
✅ Отображаются целевые слова
✅ Пользователь может ввести перевод
```

## Статус

✅ Исправлена логика индексации на фронтенде  
✅ Бэкенд возвращает все необходимые поля  
✅ Добавлена защита от undefined  
✅ Добавлено логирование для отладки  
✅ Проект успешно собирается  
✅ Готово к тестированию

---

**Версия:** 1.16.0  
**Дата:** 2026-01-15
