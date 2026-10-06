# 🚀 Деплой 101slovo на удалённый сервер

## Проблема "Failed to fetch"

Если вы видите ошибку "Failed to fetch" при попытке авторизации на удалённом сервере, это означает, что фронтенд пытается обратиться к `http://localhost:8000`, который недоступен на клиентской машине.

## Решение

### 1. Настройте переменную окружения

Создайте файл `.env` в корне проекта:

```bash
# Для удалённого сервера
VITE_API_URL=https://api.yourdomain.com

# Или если фронтенд и бэкенд на одном домене
VITE_API_URL=/api
```

**Важно:** Переменная должна начинаться с `VITE_`, чтобы быть доступной в фронтенде.

### 2. Пересоберите фронтенд

```bash
npm run build
```

### 3. Настройте CORS на бэкенде

В файле `backend/.env` добавьте ваш домен фронтенда:

```env
CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]
```

### 4. Настройте Nginx (опционально)

Если вы используете Nginx для проксирования, добавьте конфигурацию:

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
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Если используете эту конфигурацию, установите:
```env
VITE_API_URL=/api
```

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

## Автоматическое исправление URL

Если вы уже развернули проект и нужно исправить все захардкоженные URL, выполните:

```bash
python fix_api_urls.py
```

Этот скрипт заменит все `http://localhost:8000` на `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}`.

После этого пересоберите фронтенд:

```bash
npm run build
```

## Статус

✅ Создан API клиент с переменной окружения  
✅ Создан скрипт для автоматического исправления URL  
✅ Создан `.env.example` с инструкциями  
✅ Создана документация по деплою  
✅ Исправлен `src/store/auth.ts`  
✅ Проект успешно собирается

---

**Версия:** 1.0  
**Дата:** 2026-01-15
