# 101slovo Backend

FastAPI-сервер для приложения интервального повторения английских слов.

## Структура

```
backend/
├── app/
│   ├── main.py              # Точка входа, FastAPI instance, lifespan
│   ├── config.py            # Pydantic Settings для .env
│   ├── db/
│   │   └── pool.py          # psycopg_pool (AsyncConnectionPool)
│   ├── api/
│   │   ├── deps.py          # Зависимости (get_db, get_current_user)
│   │   └── v1/              # Роутеры (auth, lessons, admin и т.д.)
│   ├── core/
│   │   ├── security.py      # JWT, bcrypt, хеширование
│   │   └── exceptions.py    # Кастомные исключения и обработчики
│   ├── services/            # Бизнес-логика (SRS, LLM client, etc.)
│   └── schemas/             # Pydantic-модели для запросов/ответов
├── requirements.txt
├── .env.example
└── README.md
```

## Запуск

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Скопировать .env и заполнить
cp .env.example .env

# 3. Применить миграции
psql -d 101slovo -f ../sql/001_init.sql

# 4. Запустить сервер
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Проверка работоспособности |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

## Технологии

- **Python 3.12+**
- **FastAPI** — async web framework
- **psycopg 3** — async PostgreSQL driver
- **psycopg_pool** — connection pooling
- **PyJWT** — JWT tokens
- **bcrypt** — password hashing
- **httpx** — async HTTP client (для GigaChat)
