"""
101slovo — Кастомные исключения и их обработчики для FastAPI.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ─── Custom Exceptions ────────────────────────────────────────────────

class AppError(Exception):
    """Базовое исключение приложения."""

    def __init__(self, detail: str, status_code: int = 400, code: str | None = None):
        self.detail = detail
        self.status_code = status_code
        self.code = code
        super().__init__(detail)


class UnauthorizedError(AppError):
    """Неавторизованный доступ."""

    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(detail=detail, status_code=401, code="unauthorized")


class ForbiddenError(AppError):
    """Доступ запрещён."""

    def __init__(self, detail: str = "Forbidden"):
        super().__init__(detail=detail, status_code=403, code="forbidden")


class NotFoundError(AppError):
    """Ресурс не найден."""

    def __init__(self, detail: str = "Not found"):
        super().__init__(detail=detail, status_code=404, code="not_found")


class ConflictError(AppError):
    """Конфликт (например, email уже занят)."""

    def __init__(self, detail: str = "Conflict"):
        super().__init__(detail=detail, status_code=409, code="conflict")


class ValidationError(AppError):
    """Ошибка валидации бизнес-логики."""

    def __init__(self, detail: str = "Validation failed"):
        super().__init__(detail=detail, status_code=422, code="validation_error")


class RateLimitError(AppError):
    """Превышен лимит запросов."""

    def __init__(self, detail: str = "Too many requests"):
        super().__init__(detail=detail, status_code=429, code="rate_limited")


# ─── LLM Exceptions ───────────────────────────────────────────────────

class LlmError(Exception):
    """Базовое исключение для ошибок LLM."""

    def __init__(self, message: str, error_code: str | None = None):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class LlmUnavailable(LlmError):
    """503 llm_unavailable"""

    def __init__(self, message: str = "LLM service unavailable"):
        super().__init__(message, "llm_unavailable")


class LlmQuotaExceeded(LlmError):
    """503 llm_unavailable (квота исчерпана)"""

    def __init__(self, message: str = "LLM quota exceeded"):
        super().__init__(message, "llm_unavailable")


class LlmInvalidResponse(LlmError):
    """503 llm_invalid_response"""

    def __init__(self, message: str = "Invalid LLM response"):
        super().__init__(message, "llm_invalid_response")


class LlmRefused(LlmError):
    """422 llm_refused"""

    def __init__(self, message: str = "LLM refused to process"):
        super().__init__(message, "llm_refused")


# ─── Exception Handlers ───────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Регистрация обработчиков исключений."""

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError):
        body: dict = {"detail": exc.detail}
        if exc.code:
            body["code"] = exc.code
        return JSONResponse(status_code=exc.status_code, content=body)
