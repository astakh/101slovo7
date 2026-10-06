# 🔧 Исправление URL GigaChat API

## Дата
2026-01-15

## Проблема

При запуске урока возникала ошибка:
```
LLM generation failed: Unexpected HTTP 404
POST /lesson/start HTTP/1.1" 503 Service Unavailable
```

## Причина

**С 17 июля 2026 года Sber изменил URL для GigaChat API:**

- ❌ **Старый URL** (больше не работает для новых подключений):
  ```
  https://gigachat.devices.sberbank.ru/api/v1/chat/completions
  ```

- ✅ **Новый URL** (целевой для всех пользователей):
  ```
  https://api.giga.chat/api/v1/chat/completions
  ```

**Источник:** https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/gigachat-api

> "С 17 июля 2026 года для подключения к GigaChat API используется адрес — `https://api.giga.chat`. Он является целевым URL для всех пользователей: физических и юридических лиц."

> "При этом прежний URL больше не используется для новых подключений и в дальнейшем будет выведен из эксплуатации."

---

## Что было исправлено

### Файл: `backend/app/services/llm/gigachat.py`

#### Метод `_make_request()` (строка 258)

**Было:**
```python
async def _make_request(
    self,
    token: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> dict:
    """Выполняет HTTP-запрос к GigaChat API."""
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    ...
```

**Стало:**
```python
async def _make_request(
    self,
    token: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> dict:
    """Выполняет HTTP-запрос к GigaChat API."""
    url = "https://api.giga.chat/api/v1/chat/completions"
    ...
```

---

## Добавленное логирование

Для отладки добавлено подробное логирование во всех методах работы с GigaChat API:

### 1. Метод `_refresh()` (OAuth)

```python
logger.info(f"🔍 GigaChat OAuth Request:")
logger.info(f"   URL: {url}")
logger.info(f"   RqUID: {rq_uid}")
logger.info(f"   Scope: {settings.GIGACHAT_SCOPE}")
logger.info(f"   Auth Key (first 10 chars): {settings.GIGACHAT_AUTH_KEY[:10]}...")

# При получении ответа:
logger.info(f"📥 GigaChat OAuth Response:")
logger.info(f"   Status: {resp.status_code}")

# При ошибке:
logger.error(f"❌ GigaChat OAuth Error:")
logger.error(f"   Status: {resp.status_code}")
logger.error(f"   Response: {resp.text}")

# При успехе:
logger.info("✅ GigaChat token refreshed successfully")
logger.info(f"   Token expires at: {self._expires_at}")
```

### 2. Метод `chat()` (начало запроса)

```python
logger.info(f"🚀 Starting GigaChat chat request")
logger.info(f"   Messages: {len(messages)}")
logger.info(f"   Temperature: {temperature}")
logger.info(f"   Max tokens: {max_tokens}")
```

### 3. Метод `_make_request()` (HTTP запрос)

```python
logger.info(f"🔍 GigaChat API Request:")
logger.info(f"   URL: {url}")
logger.info(f"   Model: {settings.GIGACHAT_MODEL}")
logger.info(f"   Messages count: {len(messages)}")
logger.info(f"   Temperature: {temperature}")
logger.info(f"   Max tokens: {max_tokens}")

# При получении ответа:
logger.info(f"📥 GigaChat API Response:")
logger.info(f"   Status: {resp.status_code}")
logger.info(f"   Headers: {dict(resp.headers)}")

# При ошибке:
logger.error(f"❌ GigaChat API Error:")
logger.error(f"   Status: {resp.status_code}")
logger.error(f"   Response: {resp.text}")
```

### 4. Метод `_chat_with_retries()` (обработка ошибок)

```python
# При HTTP ошибке:
logger.error(f"❌ GigaChat HTTP Error: {status_code}")
logger.error(f"   Response: {e.response.text[:500]}")

# Для 404:
logger.critical(f"❌ GigaChat 404 Not Found")
logger.critical(f"   URL: {e.request.url}")
logger.critical(f"   Response: {e.response.text}")
raise LlmUnavailable(f"GigaChat endpoint not found (404). Check API URL and model name.")

# Для 401:
logger.warning("🔄 GigaChat 401, refreshing token and retrying...")

# Для 429:
logger.warning(f"⚠️ GigaChat 429, retrying after {delay:.2f}s")

# Для 402:
logger.critical("❌ GigaChat quota exceeded (402)")

# Для 400:
logger.critical(f"❌ GigaChat 400: {e.response.text}")
```

---

## Проверка URL

### OAuth Endpoint

**URL:** `https://ngw.devices.sberbank.ru:9443/api/v2/oauth`

**Статус:** ✅ **Не изменился**

Согласно документации, OAuth endpoint остался прежним:
```sh
curl -L -X POST 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth' \
-H 'Content-Type: application/x-www-form-urlencoded' \
-H 'Accept: application/json' \
-H 'RqUID: <идентификатор_запроса>' \
-H 'Authorization: Basic ключ_авторизации' \
--data-urlencode 'scope=GIGACHAT_API_PERS'
```

### Chat Completions Endpoint

**URL:** `https://api.giga.chat/api/v1/chat/completions`

**Статус:** ✅ **ИСПРАВЛЕНО**

Новый целевой URL для всех API запросов (кроме OAuth).

---

## Как проверить работу

### 1. Перезапустите бэкенд

```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Проверьте логи OAuth

При запуске бэкенда должны появиться логи:
```
🔍 GigaChat OAuth Request:
   URL: https://ngw.devices.sberbank.ru:9443/api/v2/oauth
   RqUID: ...
   Scope: GIGACHAT_API_PERS
   Auth Key (first 10 chars): ...
✅ GigaChat token refreshed successfully
   Token expires at: ...
```

### 3. Запустите урок через фронтенд

В логах должны появиться:
```
🚀 Starting GigaChat chat request
   Messages: 2
   Temperature: 0.7
   Max tokens: 2048
🔍 GigaChat API Request:
   URL: https://api.giga.chat/api/v1/chat/completions
   Model: GigaChat
   Messages count: 2
   Temperature: 0.7
   Max tokens: 2048
📥 GigaChat API Response:
   Status: 200
   ...
```

### 4. Проверьте отсутствие ошибок

Не должно быть:
- ❌ `LLM generation failed: Unexpected HTTP 404`
- ❌ `POST /lesson/start HTTP/1.1" 503 Service Unavailable`

---

## Совместимость

### Для старых подключений

Согласно документации:
> "Если вы подключились до 17 июля 2026 года, вы можете продолжать использовать прежний адрес `https://gigachat.devices.sberbank.ru/` — он остается доступным."

Однако:
> "При этом прежний URL больше не используется для новых подключений и в дальнейшем будет выведен из эксплуатации."

**Рекомендация:** Использовать новый URL `https://api.giga.chat` для всех подключений.

---

## Структура URL

### OAuth (получение токена)
```
https://ngw.devices.sberbank.ru:9443/api/v2/oauth
```
- Метод: POST
- Заголовки: Authorization, RqUID, Content-Type, Accept
- Тело: scope=GIGACHAT_API_PERS

### Chat Completions (генерация текста)
```
https://api.giga.chat/api/v1/chat/completions
```
- Метод: POST
- Заголовки: Authorization (Bearer token), Content-Type
- Тело: model, messages, temperature, max_tokens

### Models (список моделей)
```
https://api.giga.chat/v1/models
```
- Метод: GET
- Заголовки: Authorization (Bearer token), Accept

---

## Статус

✅ **URL обновлён**  
✅ **Логирование добавлено**  
✅ **Проект успешно собирается**  
✅ **Готов к тестированию**

---

## Ссылки

- **Официальная документация:** https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/gigachat-api
- **Получение токена:** https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-token
- **Chat Completions:** https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-chat

---

**Версия:** 1.3.0  
**Дата:** 2026-01-15
