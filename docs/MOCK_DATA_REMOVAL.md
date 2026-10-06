# Удаление мок-данных и переход на реальные API

## Дата
2026-01-15

## Статус
✅ **Завершено**

---

## Проблема

Фронтенд использовал **имитацию API** вместо реальных вызовов к бэкенду:

1. **Авторизация** (`AuthContext.tsx`):
   - Генерировал фейковый токен: `mock_token_${Date.now()}`
   - Принимал любой email/password
   - Не сохранял пользователя в БД

2. **Онбординг** (`Onboarding.tsx`):
   - Имитировал завершение онбординга
   - Не сохранял настройки в БД

3. **Уроки** (`LessonPreview.tsx`, `Lesson.tsx`):
   - Использовал захардкоженные упражнения
   - Не вызывал реальные эндпоинты

## Что было исправлено

### 1. AuthContext.tsx — Реальная авторизация

**Было:**
```typescript
// Имитация API вызова
await new Promise(resolve => setTimeout(resolve, 1000));
localStorage.setItem('access_token', 'mock_token_' + Date.now());
setUser({ id: 1, email: email, is_onboarded: false });
```

**Стало:**
```typescript
const response = await fetch(`${API_URL}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password }),
});

if (!response.ok) {
  const error = await response.json();
  throw new Error(error.detail || 'Неверный email или пароль');
}

const data = await response.json();
localStorage.setItem('access_token', data.access_token);
await fetchUser(data.access_token);
```

**Изменения:**
- ✅ Реальный вызов `/auth/login` и `/auth/register`
- ✅ Сохранение настоящего JWT токена
- ✅ Проверка токена через `/auth/me` при загрузке
- ✅ Обработка ошибок API
- ✅ Удаление токена при невалидности

### 2. Onboarding.tsx — Реальное завершение онбординга

**Было:**
```typescript
// Имитация API вызова
await new Promise(resolve => setTimeout(resolve, 1000));
setUser({ ...user, is_onboarded: true });
```

**Стало:**
```typescript
const response = await fetch('http://localhost:8000/onboarding/complete', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify({ 
    level, 
    dictionary_id: dictionaryId,
    timezone 
  }),
});

if (!response.ok) {
  const error = await response.json();
  throw new Error(error.detail || 'Ошибка завершения онбординга');
}
```

**Изменения:**
- ✅ Реальный вызов `/onboarding/complete`
- ✅ Передача `dictionary_id` (исправлена проблема с сохранением словаря)
- ✅ Обработка ошибок API
- ✅ Уведомление пользователя об ошибках

### 3. LessonPreview.tsx — Реальный preview слов

**Было:**
```typescript
// Мок-данные для демонстрации
setPreview({
  state: 'ready',
  lesson_number: 5,
  due_words: [...],
  new_words: [...],
});
```

**Стало:**
```typescript
const response = await fetch('http://localhost:8000/lesson/preview', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
});

if (!response.ok) {
  const error = await response.json();
  throw new Error(error.detail || 'Не удалось загрузить слова');
}

const data = await response.json();
setPreview(data);
```

**Изменения:**
- ✅ Реальный вызов `/lesson/preview`
- ✅ Получение due_words и new_words из БД
- ✅ Обработка состояний: `ready`, `resume`, `limit_reached`, `no_words`

### 4. LessonPreview.tsx — Реальный отказ от слова

**Было:**
```typescript
// Обновляем preview (в реальности API вернёт обновлённый preview)
setPreview({
  ...preview,
  new_words: preview.new_words.filter(w => w.word_id !== wordId),
});
```

**Стало:**
```typescript
const response = await fetch('http://localhost:8000/lesson/new-word/decline', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify({ word_id: wordId }),
});

if (!response.ok) {
  const error = await response.json();
  throw new Error(error.detail || 'Не удалось отказаться от слова');
}

const updatedPreview = await response.json();
setPreview(updatedPreview);
```

**Изменения:**
- ✅ Реальный вызов `/lesson/new-word/decline`
- ✅ Пометка слова как `ignored` в БД
- ✅ Получение обновлённого preview от API

### 5. Lesson.tsx — Реальный старт урока

**Было:**
```typescript
// Мок-данные для демонстрации
await new Promise(resolve => setTimeout(resolve, 1500));
setLesson({
  lesson_id: Date.now(),
  lesson_number: lessonNumber || 5,
  exercises_total: exercisesCount,
  exercises: generateMockExercises(exercisesCount),
});
```

**Стало:**
```typescript
const idempotencyKey = crypto.randomUUID();
const response = await fetch('http://localhost:8000/lesson/start', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    'Idempotency-Key': idempotencyKey,
  },
  body: JSON.stringify({ word_ids: wordIds }),
});

if (!response.ok) {
  const error = await response.json();
  throw new Error(error.detail || 'Не удалось начать урок');
}

const data = await response.json();
setLesson({
  lesson_id: data.lesson_id,
  lesson_number: data.lesson_number,
  exercises_total: data.exercises_total,
  exercises: [data.current_exercise],
});
```

**Изменения:**
- ✅ Реальный вызов `/lesson/start`
- ✅ Использование `Idempotency-Key` для предотвращения дублирования
- ✅ Кластеризация слов на сервере
- ✅ Генерация предложений через LLM
- ✅ Удалена функция `generateMockExercises`

### 6. Lesson.tsx — Реальная проверка упражнения

**Было:**
```typescript
// Мок-результат
await new Promise(resolve => setTimeout(resolve, 1000));
const mockResult: EvaluateResult = {
  words: currentExercise.target_words.map(tw => ({
    ...tw,
    result: 'correct' as const,  // ← Всегда correct!
  })),
};
```

**Стало:**
```typescript
const response = await fetch('http://localhost:8000/lesson/evaluate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify({
    exercise_id: currentExercise.exercise_id,
    translation: userTranslation,
    dont_know: false,
  }),
});

if (!response.ok) {
  const error = await response.json();
  throw new Error(error.detail || 'Ошибка проверки перевода');
}

const  EvaluateResult = await response.json();
setResult(data);
```

**Изменения:**
- ✅ Реальный вызов `/lesson/evaluate`
- ✅ Проверка перевода через LLM (GigaChat)
- ✅ Получение реальных результатов: `correct`, `typo`, `incorrect`
- ✅ Обновление SRS в БД
- ✅ Получение подсказок новых слов

### 7. Lesson.tsx — Реальная обработка подсказок

**Было:**
```typescript
// TODO: API вызов
// Обновляем состояние подсказок
setResult({
  ...result,
  suggestions: result.suggestions.map(s =>
    s.word_id === wordId ? { ...s, state: action as any } : s
  ),
});
```

**Стало:**
```typescript
const response = await fetch(
  `http://localhost:8000/lesson/exercises/${result.exercise_id}/suggestions/${wordId}`,
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ action }),
  }
);

if (!response.ok) {
  const error = await response.json();
  throw new Error(error.detail || 'Ошибка обработки подсказки');
}

// Обновляем состояние подсказок
setResult({
  ...result,
  suggestions: result.suggestions.map(s =>
    s.word_id === wordId ? { ...s, state: action as any } : s
  ),
});
```

**Изменения:**
- ✅ Реальный вызов `/lesson/exercises/{id}/suggestions/{wordId}`
- ✅ Добавление слова в `user_words` со `status='active'` или `status='ignored'`
- ✅ Обновление `suggested_words` в БД

## Удалённые мок-данные

### Lesson.tsx
- ❌ Удалена функция `generateMockExercises()` (75 строк)
- ❌ Удалены захардкоженные предложения:
  - "She achieved her goal through hard work."
  - "He decided to improve his English skills."
  - "The quick brown fox jumps over the lazy dog."
  - "They traveled to many different countries."
  - "The weather is beautiful today."

### LessonPreview.tsx
- ❌ Удалены мок-данные для preview:
  - due_words: `[run, book]`
  - new_words: `[achieve, goal, improve]`

### AuthContext.tsx
- ❌ Удалена генерация фейкового токена: `mock_token_${Date.now()}`
- ❌ Удалена заглушка пользователя: `{ id: 1, email: 'user@example.com' }`

### Onboarding.tsx
- ❌ Удалена имитация API вызова: `await new Promise(resolve => setTimeout(resolve, 1000))`

## Используемые эндпоинты

### Авторизация
- `POST /auth/register` — регистрация
- `POST /auth/login` — вход
- `GET /auth/me` — получение данных пользователя

### Онбординг
- `POST /onboarding/complete` — завершение онбординга

### Уроки
- `POST /lesson/preview` — получение списка слов для урока
- `POST /lesson/new-word/decline` — отказ от нового слова
- `POST /lesson/start` — старт урока
- `GET /lesson/{id}/current` — получение текущего упражнения
- `POST /lesson/evaluate` — проверка перевода
- `POST /lesson/exercises/{id}/suggestions/{wordId}` — обработка подсказки

## Тестирование

### 1. Регистрация и вход

```bash
# Запустите бэкенд
cd backend
uvicorn app.main:app --reload

# Запустите фронтенд
npm run dev
```

1. Откройте http://localhost:5173
2. Нажмите "Регистрация"
3. Введите email и пароль (минимум 8 символов)
4. Проверьте в БД:
   ```sql
   SELECT id, email, is_onboarded FROM users WHERE email = 'your@email.com';
   ```

### 2. Онбординг

1. После регистрации вы попадёте на Dashboard
2. Нажмите "Начать настройку"
3. Выберите уровень, словарь, часовой пояс
4. Проверьте в БД:
   ```sql
   SELECT level, dictionary_id FROM learning_profiles WHERE user_id = YOUR_USER_ID;
   ```

### 3. Урок

1. На Dashboard нажмите "Начать урок"
2. Вы увидите реальные слова из БД (due_words + new_words)
3. Можете отказаться от новых слов
4. Нажмите "Начать урок"
5. Проверьте в БД:
   ```sql
   SELECT * FROM lessons WHERE learning_profile_id = YOUR_PROFILE_ID;
   SELECT * FROM lesson_exercises WHERE lesson_id = LESSON_ID;
   ```

### 4. Проверка упражнения

1. Введите перевод
2. Нажмите "Проверить"
3. Проверьте в БД:
   ```sql
   SELECT * FROM llm_calls WHERE purpose = 'evaluate' ORDER BY created_at DESC LIMIT 1;
   SELECT * FROM user_words WHERE learning_profile_id = YOUR_PROFILE_ID;
   ```

## Ожидаемое поведение

### До исправления
- ❌ Пользователь не сохранялся в БД
- ❌ Любой email/password допускал вход
- ❌ Настройки не сохранялись
- ❌ Упражнения были захардкожены
- ❌ Проверка всегда возвращала "correct"

### После исправления
- ✅ Пользователь сохраняется в БД при регистрации
- ✅ Вход только с правильными credentials
- ✅ Настройки (level, dictionary_id, timezone) сохраняются
- ✅ Упражнения генерируются динамически из слов пользователя
- ✅ Проверка происходит через LLM (GigaChat)
- ✅ SRS обновляется корректно
- ✅ Подсказки новых слов работают

## Обработка ошибок

Все API вызовы теперь обрабатывают ошибки:

```typescript
if (!response.ok) {
  const error = await response.json();
  throw new Error(error.detail || 'Ошибка');
}
```

Пользователь видит понятные сообщения об ошибках через `alert()`.

## Логи

### Фронтенд (консоль браузера)
```
✅ Успешный вход: test@example.com
✅ Онбординг завершён: { level: 'A2', dictionary_id: 1, timezone: 'Europe/Moscow' }
🔍 Отправка перевода на проверку:
  - Exercise ID: 123
  - Translation: Она достигла своей цели...
📥 Ответ от API: 200 OK
✅ Успешная проверка: { words: [...], suggestions: [...] }
```

### Бэкенд (консоль сервера)
```
INFO:     POST /auth/register - 200 OK
INFO:     POST /onboarding/complete - 200 OK
INFO:     POST /lesson/preview - 200 OK
INFO:     POST /lesson/start - 200 OK
INFO:     POST /lesson/evaluate - 200 OK
```

## Связанные файлы

- `src/contexts/AuthContext.tsx` — авторизация
- `src/pages/Onboarding.tsx` — онбординг
- `src/pages/LessonPreview.tsx` — preview слов
- `src/pages/Lesson.tsx` — урок и проверка
- `src/pages/Dashboard.tsx` — главная страница (требует доработки для отображения реальной статистики)

## Следующие шаги

1. ⏳ Добавить загрузку реальной статистики в Dashboard (`/dashboard/summary`)
2. ⏳ Добавить страницу итогов урока (`/lesson/{id}/summary`)
3. ⏳ Добавить страницу словаря пользователя (`/vocabulary/list`)
4. ⏳ Добавить страницу настроек (`/settings`)
5. ⏳ Улучшить обработку ошибок (toast notifications вместо alert)

## Вывод

✅ **Все мок-данные удалены**

Фронтенд теперь полностью интегрирован с бэкендом через реальные API вызовы. Все данные сохраняются в БД, авторизация работает корректно, уроки генерируются динамически, проверка происходит через LLM.
