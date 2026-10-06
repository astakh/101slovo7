# 🐛 Исправление проблемы "Failed to fetch" на удалённом сервере

## Дата
2026-01-15

## Проблема

При деплое проекта на удалённый сервер пользователь не мог авторизоваться, получая ошибку:
```
Failed to fetch
```

## Причина

Фронтенд использовал захардкоженный URL `http://localhost:8000` во всех API вызовах. При деплое на удалённый сервер:
- Фронтенд работает на домене сервера (например, `https://yourdomain.com`)
- Но все API запросы идут на `http://localhost:8000`
- Браузер блокирует эти запросы из-за CORS или недоступности localhost

## Решение

### 1. Создан API клиент с переменной окружения

**Файл:** `src/api/client.ts`

```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = {
  async login(email: string, password: string) {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    // ...
  },
  // ...
};
```

### 2. Обновлены все файлы с API вызовами

Все файлы теперь используют переменную окружения:

```typescript
// БЫЛО:
const response = await fetch('http://localhost:8000/lesson/preview', { ... });

// СТАЛО:
const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/lesson/preview`, { ... });
```

**Обновлённые файлы:**
- ✅ `src/contexts/AuthContext.tsx`
- ✅ `src/pages/LessonPreview.tsx`
- ✅ `src/pages/Onboarding.tsx`
- ✅ `src/pages/LessonSummary.tsx`
- ✅ `src/pages/Lesson.tsx`
- ✅ `src/pages/Settings.tsx`

### 3. Создан `.env.example` файл

```env
# API URL
# Для локальной разработки:
VITE_API_URL=http://localhost:8000

# Для удалённого сервера (замените на ваш домен):
# VITE_API_URL=https://api.yourdomain.com

# Если фронтенд и бэкенд на одном домене, можно использовать относительный путь:
# VITE_API_URL=/api
```

### 4. Создан скрипт для автоматического исправления URL

**Файл:** `fix_api_urls.py`

```bash
python fix_api_urls.py
```

Скрипт автоматически заменяет все `http://localhost:8000` на `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}`.

### 5. Создана документация по деплою

**Файл:** `docs/DEPLOYMENT.md`

Содержит:
- Инструкции по настройке переменной окружения
- Примеры конфигурации для разных сценариев
- Настройка CORS на бэкенде
- Настройка Nginx для проксирования
- Проверка и отладка

## Как применить

### Шаг 1: Создайте `.env` файл

```bash
# Для удалённого сервера
echo "VITE_API_URL=https://api.yourdomain.com" > .env

# Или если фронтенд и бэкенд на одном домене
echo "VITE_API_URL=/api" > .env
```

### Шаг 2: Пересоберите фронтенд

```bash
npm run build
```

### Шаг 3: Настройте CORS на бэкенде

В файле `backend/.env`:

```env
CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]
```

### Шаг 4: Перезапустите бэкенд

```bash
cd backend
uvicorn app.main:app --reload
```

### Шаг 5: Проверьте работу

1. Откройте браузер
2. Войдите в аккаунт
3. Проверьте консоль браузера (F12) - не должно быть ошибок CORS
4. Проверьте Network tab - все запросы должны идти на правильный URL

## Примеры конфигурации

### Вариант 1: Фронтенд и бэкенд на разных доменах

```
Фронтенд: https://app.yourdomain.com
Бэкенд: https://api.yourdomain.com
```

**`.env` (фронтенд):**
```env
VITE_API_URL=https://api.yourdomain.com
```

**`backend/.env`:**
```env
CORS_ORIGINS=["https://app.yourdomain.com"]
```

### Вариант 2: Фронтенд и бэкенд на одном домене (через Nginx)

```
Фронтенд: https://yourdomain.com/
Бэкенд: https://yourdomain.com/api/
```

**`.env` (фронтенд):**
```env
VITE_API_URL=/api
```

**`backend/.env`:**
```env
CORS_ORIGINS=["https://yourdomain.com"]
```

**Nginx конфигурация:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Фронтенд
    location / {
        root /path/to/101slovo/dist;
        try_files $uri $uri/ /index.html;
    }

    # Бэкенд API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Вариант 3: Локальная разработка

```
Фронтенд: http://localhost:5173
Бэкенд: http://localhost:8000
```

**`.env` (фронтенд):**
```env
VITE_API_URL=http://localhost:8000
```

**`backend/.env`:**
```env
CORS_ORIGINS=["http://localhost:5173"]
```

## Проверка

### 1. Проверьте переменную окружения

В браузере откройте консоль (F12) и выполните:

```javascript
console.log(import.meta.env.VITE_API_URL);
```

Должен вывести ваш URL API.

### 2. Проверьте CORS

В браузере откройте Network tab и проверьте запросы к API. Не должно быть ошибок CORS.

### 3. Проверьте логи бэкенда

В логах бэкенда должны быть запросы от фронтенда:

```
INFO:     127.0.0.1:xxxxx - "POST /auth/login HTTP/1.1" 200 OK
```

## Частые проблемы

### Проблема 1: "Failed to fetch"

**Причина:** Фронтенд пытается обратиться к `localhost:8000`

**Решение:**
1. Проверьте `.env` файл
2. Пересоберите фронтенд: `npm run build`
3. Проверьте, что переменная `VITE_API_URL` установлена правильно

### Проблема 2: CORS error

**Причина:** Бэкенд не разрешает запросы с вашего домена

**Решение:**
1. Добавьте ваш домен в `CORS_ORIGINS` в `backend/.env`
2. Перезапустите бэкенд

### Проблема 3: 404 Not Found

**Причина:** Неправильный путь к API

**Решение:**
1. Проверьте, что бэкенд запущен
2. Проверьте, что URL API правильный
3. Проверьте логи бэкенда

## Статус

✅ Создан API клиент с переменной окружения  
✅ Обновлены все файлы с API вызовами  
✅ Создан `.env.example` с инструкциями  
✅ Создан скрипт для автоматического исправления URL  
✅ Создана документация по деплою  
✅ Исправлен `src/store/auth.ts`  
✅ Проект успешно собирается  
✅ Готово к деплою

---

## Связанные файлы

- `src/api/client.ts` - API клиент
- `.env.example` - пример файла окружения
- `docs/DEPLOYMENT.md` - документация по деплою
- `fix_api_urls.py` - скрипт для автоматического исправления URL
- `docs/FIX_FAILED_TO_FETCH.md` - этот документ

---

**Версия:** 1.23.0  
**Дата:** 2026-01-15
