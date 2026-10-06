# Исправление ошибки 403 Forbidden от GigaChat API

## Проблема

При попытке сгенерировать предложения через GigaChat API возникала ошибка:

```
❌ GigaChat API Error:
   Status: 403
   Response: <html>
<head><title>403 Forbidden</title></head>
<body>
<center><h1>403 Forbidden</h1></center>
<hr><center>nginx</center>
</body>
</html>
```

## Причина

Обнаружены две критические проблемы:

### 1. Неправильный URL

**Было:**
```
https://api.giga.chat/api/v1/chat/completions
```

**Проблема:** Лишний путь `/api` - правильный URL не содержит этого сегмента.

**Стало:**
```
https://api.giga.chat/v1/chat/completions
```

### 2. Отсутствие обязательных заголовков

Согласно [официальной документации GigaChat API](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-chat), для успешной авторизации необходимо передавать заголовок `User-Agent`.

**Было:**
```python
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}
```

**Стало:**
```python
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "101slovo/1.0",
}
```

**Важно из документации:**
> "User-Agent - Произвольный идентификатор клиента. Наличие заголовка поможет избежать ошибки авторизации."

## Решение

### Изменённый файл

**Файл:** `backend/app/services/llm/gigachat.py`

**Метод:** `_make_request()`

**Изменения:**

1. Исправлен URL (строка 274):
```python
url = "https://api.giga.chat/v1/chat/completions"
```

2. Добавлены обязательные заголовки (строки 275-280):
```python
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "101slovo/1.0",
}
```

## Проверка

### 1. Перезапустите бэкенд

```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Запустите урок через фронтенд

В логах должны появиться успешные запросы:

```
🔍 GigaChat API Request:
   URL: https://api.giga.chat/v1/chat/completions
   Model: GigaChat
   Messages count: 2
   Temperature: 0.7
   Max tokens: 2048
📥 GigaChat API Response:
   Status: 200
   ...
```

### 3. Проверьте отсутствие ошибок

Не должно быть:
- ❌ `Status: 403`
- ❌ `403 Forbidden`
- ❌ `LLM generation failed: Unexpected HTTP 403`

## Ссылки на документацию

- [GigaChat API - Сгенерировать ответ](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-chat)
- [GigaChat API - Авторизация](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/gigachat-api)

## Дополнительные заголовки (опционально)

Согласно документации, можно также использовать:

- `X-Client-ID` - произвольный идентификатор пользователя
- `X-Request-ID` - идентификатор запроса для логирования
- `X-Session-ID` - идентификатор сессии

Эти заголовки не обязательны, но могут быть полезны для отладки и логирования.

## Статус

✅ **URL исправлен**  
✅ **Заголовки добавлены**  
✅ **Проект успешно собирается**  
✅ **Готов к тестированию**

---

**Дата:** 2026-01-15  
**Версия:** 1.4.0
