# Страница урока (Lesson)

## Описание

Страница урока (`/lesson`) — это основное рабочее пространство пользователя, где происходит изучение слов через перевод предложений.

**Важно:** Упражнения формируются динамически из слов пользователя, а не захардкожены.

## Архитектура

Поток данных:
```
Dashboard → LessonPreview → Lesson → Summary
              (выбор слов)   (решение)  (итоги)
```

### 1. LessonPreview (`/lesson-preview`)

При нажатии "Начать урок" на Dashboard пользователь попадает на страницу выбора слов:

1. Вызывается `POST /lesson/preview` → получаем due_words + new_words
2. Пользователь видит список слов:
   - **Повторение** (due_words) — слова, которые пора повторить
   - **Новые слова** (new_words) — можно отказаться от некоторых
3. Пользователь может:
   - Отказаться от новых слов (`POST /lesson/new-word/decline`)
   - Подтвердить набор → переход на `/lesson`

### 2. Lesson (`/lesson`)

При переходе на `/lesson`:

1. Из `location.state` получаем `wordIds` и `lessonNumber`
2. Вызывается `POST /lesson/start` с `Idempotency-Key`:
   - Сервер кластеризует слова в группы (1-3 слова)
   - Для каждой группы GigaChat генерирует предложение
   - Валидирует ответ (10 правил)
   - Сохраняет урок и упражнения в БД
3. Получаем список упражнений и начинаем решать

### 3. Решение упражнений

Для каждого упражнения:

1. **Ввод перевода** — пользователь вводит перевод на русский
2. **Проверка** — вызывается `POST /lesson/evaluate`:
   - GigaChat оценивает перевод каждого целевого слова
   - Возвращает `result` (correct/typo/incorrect) для каждого слова
   - Возвращает `user_fragment` — фрагмент перевода пользователя
   - Предлагает новые слова для изучения (до 3)
3. **Результат** — показывается:
   - Статус (правильно/неправильно)
   - Эталонный перевод
   - Результаты по каждому слову
   - Подсказки новых слов (можно добавить или пропустить)
4. **Переход** — кнопка "Следующее упражнение"

### 4. Кнопка "Не знаю"

Если пользователь не знает перевод:
- Вызывается `POST /lesson/evaluate` с `dont_know: true`
- Все слова помечаются как `incorrect`
- LLM не вызывается
- Показывается эталонный перевод

### 5. Завершение урока

После последнего упражнения:
- Кнопка меняется на "Завершить урок"
- При нажатии → переход на `/lesson/{id}/summary`
- Сервер автоматически завершает урок (статус `completed`)

## Структура страниц

### LessonPreview.tsx

```
LessonPreview.tsx
├── Header (Назад, Урок N)
├── Due Words (повторение)
│   └── Список слов для повторения
├── New Words (новые слова)
│   └── Список новых слов с кнопкой "Отказаться"
└── Action Buttons (Отмена / Начать урок)
```

### Lesson.tsx

```
Lesson.tsx
├── Header
│   ├── Кнопка "Назад" (→ Dashboard)
│   ├── Название урока
│   └── Прогресс (упражнение X / Y)
├── Exercise Card (с анимацией перехода)
│   ├── Sentence (английское предложение)
│   ├── Target Words (целевые слова, выделены)
│   ├── User Input (текстовое поле)
│   ├── Buttons (Не знаю / Проверить)
│   └── Result (после проверки)
│       ├── Status (правильно/неправильно)
│       ├── Reference Translation
│       ├── Word Results (с оценками)
│       ├── Suggestions (подсказки новых слов)
│       └── Next Button (или "Завершить урок")
```

## Динамическое формирование упражнений

Упражнения НЕ захардкожены. Они формируются на сервере:

1. **Кластеризация слов** — слова разбиваются на группы по 1-3 слова
2. **Генерация предложений** — для каждой группы GigaChat создаёт предложение
3. **Валидация** — проверяется соответствие 10 правилам
4. **Сохранение** — упражнения сохраняются в БД

Пример:
- Вход: 5 слов `[run, book, achieve, goal, improve]`
- Кластеризация: `[[run, book], [achieve, goal], [improve]]`
- GigaChat генерирует:
  - "She runs to the book store."
  - "He achieved his goal through hard work."
  - "I want to improve my skills."

## API интеграция

### Текущая реализация (заглушки)

Сейчас используются мок-данные для демонстрации:
- `LessonPreview.tsx` — мок-данные слов (due_words + new_words)
- `Lesson.tsx` — мок-данные упражнений и результатов проверки

### Подключение реального API

#### LessonPreview.tsx

Замените заглушку в `loadPreview()`:
```typescript
const response = await fetch('http://localhost:8000/lesson/preview', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
  },
});
const data = await response.json();
setPreview(data);
```

#### Lesson.tsx

Замените заглушку в `startNewLesson()`:
```typescript
const idempotencyKey = crypto.randomUUID();
const response = await fetch('http://localhost:8000/lesson/start', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    'Idempotency-Key': idempotencyKey,
  },
  body: JSON.stringify({ word_ids: wordIds }),
});
const data = await response.json();
// data содержит lesson_id, lesson_number, exercises_total, current_exercise
```

Замените заглушку в `handleSubmit()`:
```typescript
const response = await fetch('http://localhost:8000/lesson/evaluate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
  },
  body: JSON.stringify({
    exercise_id: currentExercise.exercise_id,
    translation: userTranslation,
    dont_know: false,
  }),
});
const data = await response.json();
// data содержит words[], suggestions[], lesson_completed
```

## Состояние

### LessonPreview.tsx
- `preview` — данные preview (state, due_words, new_words)
- `decliningWords` — Set ID слов, которые отказываются
- `loading` / `error` — состояние загрузки

### Lesson.tsx
- `lesson` — данные урока (lesson_id, exercises, exercises_total)
- `currentExerciseIndex` — индекс текущего упражнения
- `userTranslation` — ввод пользователя
- `showResult` — показывать ли результат
- `result` — результат проверки (EvaluateResult)
- `submitting` — состояние отправки

## Логика перехода между упражнениями

При нажатии "Следующее упражнение":
1. Проверяется `result.lesson_completed`
2. Если `false`:
   - Увеличивается `currentExerciseIndex`
   - Сбрасываются: `showResult`, `result`, `userTranslation`
   - Показывается новое упражнение с анимацией
3. Если `true`:
   - Переход на `/lesson/{id}/summary` (страница итогов)

На последнем упражнении:
- Кнопка меняется на "Завершить урок"
- Сервер автоматически завершает урок при последнем evaluate
- Пользователь переходит на страницу итогов

## Навигация

### LessonPreview
- **Кнопка "Назад"** — возврат на Dashboard
- **Кнопка "Отказаться"** (у новых слов) — decline слова
- **Кнопка "Начать урок"** — переход на `/lesson` с word_ids

### Lesson
- **Кнопка "Назад"** — возврат на Dashboard
- **Кнопка "Не знаю"** — пропуск упражнения (dont_know: true)
- **Кнопка "Проверить"** — отправка перевода на проверку
- **Кнопка "Следующее упражнение"** — переход к следующему
- **Кнопка "Завершить урок"** — переход на summary (на последнем)

## Тестирование

### Полный цикл:

1. **Dashboard** → нажмите "Начать урок"
2. **LessonPreview**:
   - Увидите список слов (due_words + new_words)
   - Можете отказаться от новых слов (крестик)
   - Нажмите "Начать урок"
3. **Lesson**:
   - Увидите первое предложение с целевыми словами
   - Введите перевод → "Проверить"
   - Увидите результат + подсказки новых слов
   - Можете добавить/пропустить подсказки
   - Нажмите "Следующее упражнение"
   - Повторите для всех упражнений
4. **После последнего упражнения**:
   - Кнопка "Завершить урок"
   - Переход на `/lesson/{id}/summary` (пока не реализовано)

### Обработка состояний:

- **state='resume'** → показывается "Продолжить урок"
- **state='limit_reached'** → показывается "Дневной лимит исчерпан"
- **state='no_words'** → показывается "Нет слов для изучения"
- **state='ready'** → показывается выбор слов

## Следующие шаги

### Frontend
- [ ] Заменить мок-данные на реальные API вызовы
- [ ] Реализовать страницу итогов урока (`/lesson/{id}/summary`)
- [ ] Добавить обработку ошибок с retry логикой
- [ ] Улучшить UX при длительной генерации (прогресс-бар)
- [ ] Добавить возможность вернуться к предыдущему упражнению
- [ ] Реализовать offline mode (кэширование упражнений)

### Backend
- [ ] Реализовать `POST /lesson/preview` (алгоритм 5.2)
- [ ] Реализовать `POST /lesson/new-word/decline` (алгоритм 5.3)
- [ ] Реализовать `POST /lesson/start` (алгоритм 5.4)
- [ ] Реализовать `POST /lesson/evaluate` (алгоритм 5.5)
- [ ] Реализовать `GET /lesson/{id}/summary` (алгоритм 5.6)
- [ ] Интеграция с GigaChat для генерации предложений
- [ ] Интеграция с GigaChat для оценки переводов
- [ ] Реализовать SRS алгоритм (обновление stage, due_lesson_number)

### Интеграция
- [ ] Подключить реальный GigaChat API
- [ ] Настроить промпты для генерации и оценки
- [ ] Реализовать логирование вызовов LLM
- [ ] Настроить rate limiting для LLM вызовов
- [ ] Реализовать обработку ошибок LLM (retry, fallback)
