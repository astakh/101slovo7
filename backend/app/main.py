"""
101slovo — Точка входа FastAPI-приложения.
Lifespan, middleware, роутеры.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import (
    LlmInvalidResponse,
    LlmQuotaExceeded,
    LlmRefused,
    LlmUnavailable,
    register_exception_handlers,
)
from app.db.pool import close_pool, init_pool
from app.services.llm.gigachat import token_refresh_loop

# Роутеры v1
from app.api.v1 import admin, admin_db, admin_prompts, auth, dashboard, lessons, onboarding, profile, settings as settings_router, vocabulary


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Жизненный цикл приложения.
    Startup: инициализация пула БД, запуск фоновой задачи обновления токена GigaChat.
    Shutdown: отмена фоновой задачи, закрытие пула.
    """
    # ── Startup ──────────────────────────────────────────────────────
    await init_pool()
    
    # Запуск фоновой задачи обновления токена GigaChat
    refresh_task = asyncio.create_task(token_refresh_loop())
    logger_info = __import__("logging").getLogger(__name__)
    logger_info.info("GigaChat token refresh loop started")
    
    yield
    
    # ── Shutdown ─────────────────────────────────────────────────────
    refresh_task.cancel()
    try:
        await refresh_task
    except asyncio.CancelledError:
        pass
    logger_info.info("GigaChat token refresh loop stopped")
    
    await close_pool()


app = FastAPI(
    title="101slovo API",
    description="MVP backend — интервальное повторение английских слов в контексте",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS Middleware ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,  # Обязательно для httpOnly cookie / Authorization header
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Exception Handlers ───────────────────────────────────────────────
register_exception_handlers(app)


# ─── LLM Exception Handlers ──────────────────────────────────────────
@app.exception_handler(LlmUnavailable)
async def llm_unavailable_handler(request: Request, exc: LlmUnavailable):
    return JSONResponse(
        status_code=503,
        content={"error": {"code": "llm_unavailable", "message": exc.message}},
    )


@app.exception_handler(LlmQuotaExceeded)
async def llm_quota_handler(request: Request, exc: LlmQuotaExceeded):
    return JSONResponse(
        status_code=503,
        content={"error": {"code": "llm_unavailable", "message": exc.message}},
    )


@app.exception_handler(LlmInvalidResponse)
async def llm_invalid_response_handler(request: Request, exc: LlmInvalidResponse):
    return JSONResponse(
        status_code=503,
        content={"error": {"code": "llm_invalid_response", "message": exc.message}},
    )


@app.exception_handler(LlmRefused)
async def llm_refused_handler(request: Request, exc: LlmRefused):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "llm_refused", "message": exc.message}},
    )


# ─── Routers ──────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(profile.router, prefix="/profile", tags=["Profile"])
app.include_router(settings_router.router, tags=["Settings"])
app.include_router(lessons.router, prefix="/lesson", tags=["Lesson"])
app.include_router(vocabulary.router, prefix="/vocabulary", tags=["Vocabulary"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(admin_db.router, prefix="/admin", tags=["Admin DB"])
app.include_router(admin_prompts.router, prefix="/admin", tags=["Admin Prompts"])


# ─── Health Check ─────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Проверка работоспособности сервиса."""
    return {"status": "ok"}
