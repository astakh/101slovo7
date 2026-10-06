# Отладка ошибки 401 Unauthorized при проверке упражнения

## Дата
2026-01-15

## Проблема

При попытке проверить упражнение через LLM возникает ошибка:
```
INFO:     127.0.0.1:62850 - "POST /lesson/evaluate HTTP/1.1" 401 Unauthorized
```

## Причина

**Фронтенд использует имитацию авторизации** (`src/contexts/AuthContext.tsx`), которая генерирует фейковый токен:
```typescript
localStorage.setItem('access_token', 'mock_token_' + Date.now());
```

Это **не настоящий JWT токен**, поэтому бэкенд не может его декодировать и возвращает 401 Unauthorized.

## Добавленное логирование

### Фронтенд (`src/pages/Lesson.tsx`)

Добавлено логирование в консоль браузера:
```typescript
console.log('🔍 Отладка проверки упражнения:');
console.log('  - Exercise ID:', currentExercise.exercise_id);
console.log('  - Token:', token ? `${token.substring(0, 20)}...` : 'ОТСУТСТВУЕТ');
console.log('  - Translation:', userTranslation);
console.log('📥 Ответ от API:', response.status, response.statusText);
console.log('❌ Ошибка API:', error);
console.log('✅ Успешная проверка:', data);
```

### Бэкенд (`backend/app/api/deps.py`)

Добавлено логирование в консоль сервера:
```python
logger.info(f"🔍 Получен токен: {token_preview}")
logger.info(f"✅ Токен декодирован успешно: {payload}")
logger.error(f"❌ Неверный тип токена: {payload.get('type')}")
logger.error(f"❌ Токен истёк: {e}")
logger.error(f"❌ Невалидный токен: {e}")
```

## Как проверить проблему

### 1. Откройте консоль браузера (F12)

Перейдите на страницу урока и нажмите "Проверить". Вы увидите:

```
🔍 Отладка проверки упражнения:
  - Exercise ID: 1234567890
  - Token: mock_token_1705312345...
  - Translation: Она достигла своей цели...
📥 Ответ от API: 401 Unauthorized
❌ Ошибка API: {detail: 'invalid_token'}
```

**Проблема:** Токен начинается с `mock_token_` — это фейковый токен, не JWT.

### 2. Проверьте логи бэкенда

В терминале, где запущен `uvicorn`, вы увидите:

```
🔍 Получен токен: mock_token_1705312345...
❌ Невалидный токен: Invalid token signature
INFO:     127.0.0.1:62850 - "POST /lesson/evaluate HTTP/1.1" 401 Unauthorized
```

## Решение

### Вариант 1: Подключить реальную авторизацию (рекомендуется)

Замените имитацию в `src/contexts/AuthContext.tsx` на реальные API вызовы:

```typescript
const login = async (email: string, password: string) => {
  setLoading(true);
  try {
    const response = await fetch('http://localhost:8000/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Ошибка входа');
    }
    
    const data = await response.json();
    
    // Сохраняем настоящий JWT токен
    localStorage.setItem('access_token', data.access_token);
    
    // Получаем данные пользователя
    const userResponse = await fetch('http://localhost:8000/auth/me', {
      headers: { 'Authorization': `Bearer ${data.access_token}` },
    });
    const userData = await userResponse.json();
    setUser(userData);
    
    console.log('✅ Успешный вход:', email);
  } catch (error) {
    console.error('❌ Ошибка входа:', error);
    throw error;
  } finally {
    setLoading(false);
  }
};
```

Аналогично для `register`:

```typescript
const register = async (email: string, password: string) => {
  setLoading(true);
  try {
    const response = await fetch('http://localhost:8000/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Ошибка регистрации');
    }
    
    const data = await response.json();
    
    // Сохраняем настоящий JWT токен
    localStorage.setItem('access_token', data.access_token);
    
    // Получаем данные пользователя
    const userResponse = await fetch('http://localhost:8000/auth/me', {
      headers: { 'Authorization': `Bearer ${data.access_token}` },
    });
    const userData = await userResponse.json();
    setUser(userData);
    
    console.log('✅ Успешная регистрация:', email);
  } catch (error) {
    console.error('❌ Ошибка регистрации:', error);
    throw error;
  } finally {
    setLoading(false);
  }
};
```

### Вариант 2: Быстрое тестирование (временное решение)

Если нужно быстро протестировать проверку упражнения, можно вручную получить настоящий токен:

1. **Зарегистрируйтесь через Swagger UI:**
   - Откройте http://localhost:8000/docs
   - Найдите `POST /auth/register`
   - Нажмите "Try it out"
   - Введите:
     ```json
     {
       "email": "test@example.com",
       "password": "password123"
     }
     ```
   - Нажмите "Execute"
   - Скопируйте `access_token` из ответа

2. **Вставьте токен в консоль браузера:**
   ```javascript
   localStorage.setItem('access_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...');
   ```

3. **Обновите страницу** и попробуйте проверить упражнение снова.

## Проверка JWT токена

### Как выглядит настоящий JWT токен

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzA1MzE1OTQ1LCJpYXQiOjE3MDUzMTQxNDUsInR5cGUiOiJhY2Nlc3MifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

Структура:
- **Header:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9` (base64)
- **Payload:** `eyJzdWIiOiIxIiwiZXhwIjoxNzA1MzE1OTQ1LCJpYXQiOjE3MDUzMTQxNDUsInR5cGUiOiJhY2Nlc3MifQ` (base64)
- **Signature:** `SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c`

### Как декодировать JWT

Используйте https://jwt.io/ для проверки токена.

Вставьте токен и увидите:
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
{
  "sub": "1",
  "exp": 1705315945,
  "iat": 1705314145,
  "type": "access"
}
```

## Полный цикл тестирования

### 1. Запустите бэкенд
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Запустите фронтенд
```bash
npm run dev
```

### 3. Зарегистрируйтесь через Swagger UI
- Откройте http://localhost:8000/docs
- `POST /auth/register` с email и password
- Скопируйте `access_token`

### 4. Вставьте токен в консоль браузера
```javascript
localStorage.setItem('access_token', 'YOUR_JWT_TOKEN_HERE');
```

### 5. Обновите страницу и пройдите онбординг

### 6. Начните урок и проверьте упражнение

### 7. Проверьте логи

**В консоли браузера:**
```
🔍 Отладка проверки упражнения:
  - Exercise ID: 1234567890
  - Token: eyJhbGciOiJIUzI1NiIs...
  - Translation: Она достигла своей цели...
📥 Ответ от API: 200 OK
✅ Успешная проверка: {words: [...], suggestions: [...]}
```

**В логах бэкенда:**
```
🔍 Получен токен: eyJhbGciOiJIUzI1NiIs...
✅ Токен декодирован успешно: {'sub': '1', 'exp': 1705315945, 'type': 'access'}
✅ User ID извлечён: 1
INFO:     127.0.0.1:62850 - "POST /lesson/evaluate HTTP/1.1" 200 OK
```

## Ожидаемые результаты

### Успешная проверка
- Статус: 200 OK
- Ответ содержит `words[]` с результатами для каждого слова
- Ответ содержит `suggestions[]` с подсказками новых слов
- SRS обновлён в БД

### Ошибки

#### 401 Unauthorized
- **Причина:** Невалидный или отсутствующий токен
- **Решение:** Получить настоящий JWT токен через `/auth/login` или `/auth/register`

#### 403 Forbidden
- **Причина:** Токен валиден, но пользователь не найден в БД
- **Решение:** Проверить, что пользователь существует в таблице `users`

#### 500 Internal Server Error
- **Причина:** Ошибка на сервере (LLM недоступен, БД недоступна)
- **Решение:** Проверить логи бэкенда

## Следующие шаги

1. ✅ Добавлено логирование для отладки
2. ⏳ Подключить реальную авторизацию в `AuthContext.tsx`
3. ⏳ Протестировать полный цикл: регистрация → онбординг → урок → проверка
4. ⏳ Проверить, что SRS обновляется корректно
5. ⏳ Проверить, что подсказки новых слов работают

## Связанные файлы

- `src/contexts/AuthContext.tsx` — авторизация (требует исправления)
- `src/pages/Lesson.tsx` — проверка упражнения (добавлено логирование)
- `backend/app/api/deps.py` — извлечение user_id из токена (добавлено логирование)
- `backend/app/api/v1/lessons.py` — эндпоинт `/lesson/evaluate`
- `backend/app/services/lesson_evaluate.py` — сервис оценки упражнения
