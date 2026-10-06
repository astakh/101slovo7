# 🐛 Исправление ошибки "Cannot read properties of undefined (reading 'sentence')"

## Дата
2026-01-15

## Проблема

При переходе к следующему упражнению после проверки текущего возникала ошибка:

```
❌ Current exercise is undefined!
   lesson.exercises: [{…}]
   currentExerciseIndex: 1
```

## Причина

**Архитектурная проблема:**

1. При загрузке урока через `GET /lesson/{id}/current` бэкенд возвращает только **ОДНО** текущее упражнение
2. Фронтенд сохраняет его в массив `exercises: [data.current_exercise]`
3. После проверки упражнения вызывается `handleNext`, который увеличивает `currentExerciseIndex`
4. Но массив `exercises` **не обновляется** следующим упражнением
5. При обращении к `lesson.exercises[1]` получаем `undefined`
6. При обращении к `undefined.sentence` получаем ошибку

**Пример:**
```
Начальное состояние:
  lesson.exercises = [{ exercise_id: 1, sentence: "..." }]
  currentExerciseIndex = 0
  ✅ lesson.exercises[0] существует

После handleNext:
  lesson.exercises = [{ exercise_id: 1, sentence: "..." }]  // НЕ изменился!
  currentExerciseIndex = 1  // Увеличился!
  ❌ lesson.exercises[1] = undefined
```

## Решение

Изменена функция `handleNext` в `src/pages/Lesson.tsx`:

**Было:**
```typescript
const handleNext = () => {
  if (!lesson || !result) return;
  
  if (result.lesson_completed) {
    navigate(`/lesson/${lesson.lesson_id}/summary`);
  } else {
    // Просто увеличиваем индекс
    setCurrentExerciseIndex(currentExerciseIndex + 1);
    setShowResult(false);
    setResult(null);
    setUserTranslation('');
  }
};
```

**Стало:**
```typescript
const handleNext = async () => {
  if (!lesson || !result) return;
  
  console.log('🔍 handleNext called');
  console.log('   lesson_completed:', result.lesson_completed);
  
  if (result.lesson_completed) {
    console.log('✅ Lesson completed, navigating to summary');
    navigate(`/lesson/${lesson.lesson_id}/summary`);
  } else {
    // Загружаем следующее упражнение через API
    console.log('📝 Loading next exercise...');
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Токен авторизации отсутствует');
      }

      const response = await fetch(`http://localhost:8000/lesson/${lesson.lesson_id}/current`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Не удалось загрузить следующее упражнение');
      }

      const data = await response.json();
      console.log('📥 Next exercise loaded:', data);

      if (!data.current_exercise) {
        throw new Error('Следующее упражнение не найдено');
      }

      // Обновляем массив упражнений
      setLesson({
        ...lesson,
        exercises: [data.current_exercise],
      });
      
      // Сбрасываем индекс и состояние
      setCurrentExerciseIndex(0);
      setShowResult(false);
      setResult(null);
      setUserTranslation('');
      
      console.log('✅ Next exercise set successfully');
    } catch (err) {
      console.error('❌ Error loading next exercise:', err);
      setError(err instanceof Error ? err.message : 'Не удалось загрузить следующее упражнение');
    }
  }
};
```

**Ключевые изменения:**
1. Функция стала `async`
2. Добавлен вызов API `GET /lesson/{id}/current` для получения следующего упражнения
3. Массив `exercises` обновляется новым упражнением
4. `currentExerciseIndex` сбрасывается в 0 (всегда работаем с первым элементом массива)
5. Добавлено логирование для отладки
6. Добавлена обработка ошибок

## Как работает бэкенд

Эндпоинт `GET /lesson/{id}/current` (файл `backend/app/services/lesson_resume.py`):

```python
# Получаем первое невыполненное упражнение
cur = await db.execute(
    """SELECT id, order_index, target_sentence, reference_translation, target_words
       FROM lesson_exercises 
       WHERE lesson_id = %s AND status = 'pending' 
       ORDER BY order_index LIMIT 1""",
    [lesson_id],
)
current = await cur.fetchone()
```

**Логика:**
- После проверки упражнения его статус меняется с `pending` на `evaluated`
- Следующий вызов `/lesson/{id}/current` вернёт следующее упражнение со статусом `pending`
- Если все упражнения выполнены, вернётся `lesson_not_active`

## Поток данных

### 1. Загрузка урока
```
Frontend → GET /lesson/1/current
Backend → { current_exercise: { exercise_id: 1, ... } }
Frontend → lesson.exercises = [exercise_1]
           currentExerciseIndex = 0
```

### 2. Проверка упражнения
```
Frontend → POST /lesson/evaluate { exercise_id: 1, ... }
Backend → { result: 'correct', lesson_completed: false }
Frontend → Показывает результат проверки
```

### 3. Переход к следующему упражнению
```
Frontend → handleNext()
           ↓
           GET /lesson/1/current
           ↓
Backend → { current_exercise: { exercise_id: 2, ... } }
           ↓
Frontend → lesson.exercises = [exercise_2]
           currentExerciseIndex = 0
           Показывает следующее упражнение
```

### 4. Завершение урока
```
Frontend → POST /lesson/evaluate { exercise_id: N, ... }
Backend → { result: 'correct', lesson_completed: true }
Frontend → handleNext()
           ↓
           navigate('/lesson/1/summary')
```

## Как проверить

### 1. Перезапустите фронтенд
```bash
npm run dev
```

### 2. Создайте новый урок
1. Перейдите на Dashboard
2. Нажмите "Начать урок"
3. Выберите слова
4. Нажмите "Начать урок"

### 3. Пройдите несколько упражнений
1. Введите перевод
2. Нажмите "Проверить"
3. Нажмите "Следующее упражнение"
4. Повторите для нескольких упражнений

### 4. Проверьте консоль браузера (F12)
Должны быть логи:
```
🔍 handleNext called
   lesson_completed: false
📝 Loading next exercise...
📥 Next exercise loaded: { lesson_id: 1, current_exercise: {...} }
✅ Next exercise set successfully
```

### 5. Завершите урок
1. Пройдите все упражнения
2. На последнем упражнении нажмите "Проверить"
3. Нажмите "Завершить урок"
4. Должен произойти переход на страницу итогов

## Ожидаемое поведение

### До исправления
```
❌ Uncaught TypeError: Cannot read properties of undefined (reading 'sentence')
   at Lesson (Lesson.tsx:382:36)
```

### После исправления
```
✅ Упражнение успешно загружается
✅ Пользователь вводит перевод
✅ Пользователь нажимает "Проверить"
✅ Показывается результат проверки
✅ Пользователь нажимает "Следующее упражнение"
✅ Загружается следующее упражнение
✅ Цикл повторяется до завершения урока
✅ Переход на страницу итогов
```

## Альтернативные решения (не реализованы)

### Вариант 1: Загружать все упражнения сразу
**Плюсы:**
- Меньше запросов к API
- Быстрее переключение между упражнениями

**Минусы:**
- Больше данных передаётся за один раз
- Нужно изменять бэкенд

### Вариант 2: Хранить все упражнения в состоянии
**Плюсы:**
- Не нужно загружать каждое упражнение отдельно

**Минусы:**
- Нужно изменять бэкенд, чтобы возвращал все упражнения
- Больше памяти используется

### Выбранный вариант: Загружать следующее упражнение по запросу
**Плюсы:**
- Не нужно изменять бэкенд
- Минимальное использование памяти
- Простая логика

**Минусы:**
- Дополнительный запрос к API при каждом переходе
- Небольшая задержка при переходе

## Статус

✅ Исправлена функция `handleNext`  
✅ Добавлена загрузка следующего упражнения через API  
✅ Добавлено логирование для отладки  
✅ Добавлена обработка ошибок  
✅ Проект успешно собирается  
✅ Готово к тестированию

---

**Версия:** 1.17.0  
**Дата:** 2026-01-15
