# 🗑️ Удаление проверки сертификата GigaChat

## Дата
2026-01-15

## Что было изменено

### Проблема
Код содержал проверку наличия файла сертификата GigaChat с fallback на системные сертификаты. Это усложняло код и требовало наличия переменной `GIGACHAT_CA_CERT_PATH` в конфигурации.

### Решение
Удалена проверка сертификата. Теперь используется стандартный SSL контекст без указания файла сертификата.

---

## Изменённые файлы

### 1. `backend/app/services/llm/gigachat.py`

#### Метод `_refresh()` (строки 69-88)

**Было:**
```python
async def _refresh(self) -> None:
    """Обновляет токен через OAuth."""
    rq_uid = str(uuid.uuid4())
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Authorization": f"Basic {settings.GIGACHAT_AUTH_KEY}",
        "RqUID": rq_uid,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    data = {"scope": settings.GIGACHAT_SCOPE}

    # Создаём SSL контекст с обработкой отсутствия файла сертификата
    try:
        ssl_context = ssl.create_default_context(cafile=settings.GIGACHAT_CA_CERT_PATH)
    except FileNotFoundError:
        logger.warning(
            f"Сертификат GigaChat не найден: {settings.GIGACHAT_CA_CERT_PATH}. "
            "Используются системные сертификаты."
        )
        ssl_context = ssl.create_default_context()

    try:
        async with httpx.AsyncClient(verify=ssl_context, timeout=10.0) as client:
            ...
```

**Стало:**
```python
async def _refresh(self) -> None:
    """Обновляет токен через OAuth."""
    rq_uid = str(uuid.uuid4())
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Authorization": f"Basic {settings.GIGACHAT_AUTH_KEY}",
        "RqUID": rq_uid,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    data = {"scope": settings.GIGACHAT_SCOPE}
    ssl_context = ssl.create_default_context()

    try:
        async with httpx.AsyncClient(verify=ssl_context, timeout=10.0) as client:
            ...
```

#### Метод `_make_request()` (строки 257-291)

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
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.GIGACHAT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    # Создаём SSL контекст с обработкой отсутствия файла сертификата
    try:
        ssl_context = ssl.create_default_context(cafile=settings.GIGACHAT_CA_CERT_PATH)
    except FileNotFoundError:
        logger.warning(
            f"Сертификат GigaChat не найден: {settings.GIGACHAT_CA_CERT_PATH}. "
            "Используются системные сертификаты."
        )
        ssl_context = ssl.create_default_context()

    async with httpx.AsyncClient(verify=ssl_context, timeout=timeout) as client:
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
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.GIGACHAT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    ssl_context = ssl.create_default_context()

    async with httpx.AsyncClient(verify=ssl_context, timeout=timeout) as client:
        ...
```

---

### 2. `backend/app/config.py`

**Было:**
```python
# ─── GigaChat LLM ────────────────────────────────────────────────
GIGACHAT_AUTH_KEY: str
GIGACHAT_SCOPE: str
GIGACHAT_MODEL: str
GIGACHAT_CA_CERT_PATH: str
GIGACHAT_MAX_CONCURRENCY: int = 5
GIGACHAT_TOKEN_REFRESH_MINUTES: int = 10
```

**Стало:**
```python
# ─── GigaChat LLM ────────────────────────────────────────────────
GIGACHAT_AUTH_KEY: str
GIGACHAT_SCOPE: str
GIGACHAT_MODEL: str
GIGACHAT_MAX_CONCURRENCY: int = 5
GIGACHAT_TOKEN_REFRESH_MINUTES: int = 10
```

---

### 3. `backend/.env.example`

**Было:**
```env
# ─── GigaChat LLM ────────────────────────────────────────────────────
GIGACHAT_AUTH_KEY=your-auth-key-here
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat
GIGACHAT_CA_CERT_PATH=./certs/russian_trusted_root_ca_pem.crt
GIGACHAT_MAX_CONCURRENCY=5
GIGACHAT_TOKEN_REFRESH_MINUTES=10
```

**Стало:**
```env
# ─── GigaChat LLM ────────────────────────────────────────────────────
GIGACHAT_AUTH_KEY=your-auth-key-here
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat
GIGACHAT_MAX_CONCURRENCY=5
GIGACHAT_TOKEN_REFRESH_MINUTES=10
```

---

## Преимущества изменений

### ✅ Упрощение кода
- Удалён try/except блок с обработкой FileNotFoundError
- Удалено логирование предупреждений
- Код стал короче и понятнее

### ✅ Упрощение конфигурации
- Не нужно указывать `GIGACHAT_CA_CERT_PATH` в `.env`
- Не нужно скачивать и размещать файл сертификата
- Меньше переменных для настройки

### ✅ Использование системных сертификатов
- Python автоматически использует системные сертификаты
- Это стандартная практика для большинства приложений
- Работает "из коробки" без дополнительной настройки

---

## Как это работает

### До изменений
1. Пытались загрузить сертификат из `GIGACHAT_CA_CERT_PATH`
2. Если файл не найден → логируем предупреждение
3. Используем системные сертификаты (fallback)

### После изменений
1. Сразу используем системные сертификаты
2. Никаких предупреждений
3. Простой и понятный код

---

## Проверка

### 1. Удалите переменную из `.env`

Если у вас есть файл `backend/.env`, удалите строку:
```env
GIGACHAT_CA_CERT_PATH=./certs/russian_trusted_root_ca_pem.crt
```

### 2. Перезапустите бэкенд

```bash
cd backend
uvicorn app.main:app --reload
```

### 3. Проверьте работу GigaChat

Запустите урок через фронтенд. В логах не должно быть предупреждений о сертификатах.

---

## Совместимость

### ✅ Обратная совместимость
- Если в `.env` осталась переменная `GIGACHAT_CA_CERT_PATH`, она будет проигнорирована
- Код не будет её использовать
- Никаких ошибок не возникнет

### ✅ Python SSL
- `ssl.create_default_context()` автоматически использует системные сертификаты
- Работает на всех современных операционных системах
- Не требует дополнительной настройки

---

## Статус

✅ **Изменения внесены**  
✅ **Проект успешно собирается**  
✅ **Код упрощён**  
✅ **Конфигурация упрощена**

---

**Версия:** 1.2.0  
**Дата:** 2026-01-15
