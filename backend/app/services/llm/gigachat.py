"""
101slovo — Клиент GigaChat.
Реализует OAuth-авторизацию, фоновое обновление токена, управление параллелизмом,
обработку ошибок и два слоя: chat() и chat_json().

Изменения:
- Все print() заменены на logger.debug() / logger.info()
- Добавлена Pydantic-валидация JSON-ответов LLM
"""
import asyncio
import json
import logging
import random
import ssl
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field, field_validator

from app.config import settings
from app.core.exceptions import (
    LlmInvalidResponse,
    LlmQuotaExceeded,
    LlmRefused,
    LlmUnavailable,
)
from app.services.llm.llm_logger import log_llm_call

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Pydantic-модели для валидации JSONB от LLM
# ──────────────────────────────────────────────

class LlmWord(BaseModel):
    """Слово в ответе LLM (для generate_sentences)."""
    word_id: int
    lemma: str
    pos: str
    surface_form: str

    @field_validator("lemma")
    @classmethod
    def lemma_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("lemma must not be empty")
        return v.strip().lower()

    @field_validator("pos")
    @classmethod
    def pos_allowed(cls, v: str) -> str:
        allowed = {"noun", "verb", "adj", "adv", "pron", "prep", "conj", "num", "det", "intj"}
        if v not in allowed:
            raise ValueError(f"invalid pos: {v}")
        return v


class LlmNontargetWord(BaseModel):
    """Нецелевое слово в ответе LLM."""
    lemma: str
    pos: str
    surface_form: str


class LlmSentence(BaseModel):
    """Одно предложение в ответе generate_sentences."""
    group_index: int
    sentence: str
    reference_translation: str
    words: list[LlmWord]
    nontarget_words: list[LlmNontargetWord] = Field(default_factory=list)

    @field_validator("sentence")
    @classmethod
    def sentence_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("sentence must not be empty")
        if len(v) > 200:
            raise ValueError("sentence too long (max 200)")
        return v

    @field_validator("reference_translation")
    @classmethod
    def translation_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("reference_translation must not be empty")
        if len(v) > 300:
            raise ValueError("reference_translation too long (max 300)")
        return v


class LlmEvaluation(BaseModel):
    """Оценка одного слова в ответе evaluate_translation."""
    word_id: int
    result: str
    user_fragment: Optional[str] = None

    @field_validator("result")
    @classmethod
    def result_allowed(cls, v: str) -> str:
        allowed = {"correct", "typo", "incorrect"}
        if v not in allowed:
            raise ValueError(f"invalid result: {v}, allowed: {allowed}")
        return v


class LlmSuggestedWord(BaseModel):
    """Подсказка нового слова."""
    lemma: str
    pos: str
    translations: list[str]


class LlmTranslationError(BaseModel):
    """Ошибка перевода нецелевого слова."""
    word_id: int
    user_fragment: Optional[str] = None
    correct_translation: Optional[str] = None


class LlmEvaluateResponse(BaseModel):
    """Полный ответ evaluate_translation."""
    evaluations: list[LlmEvaluation] = Field(default_factory=list)
    new_suggested_words: list[LlmSuggestedWord] = Field(default_factory=list)
    translation_errors: list[LlmTranslationError] = Field(default_factory=list)


def validate_generate_response(raw: Any) -> list[LlmSentence]:
    """Валидирует ответ generate_sentences через Pydantic."""
    sentences_list: list[Any] = []
    if isinstance(raw, list):
        sentences_list = raw
    elif isinstance(raw, dict):
        for key in ["sentences", "groups", "results", "exercises"]:
            if key in raw and isinstance(raw[key], list):
                sentences_list = raw[key]
                break
        if not sentences_list:
            sentences_list = [raw]
    else:
        raise LlmInvalidResponse(f"Unexpected LLM response type: {type(raw)}")

    validated: list[LlmSentence] = []
    for idx, item in enumerate(sentences_list):
        if not isinstance(item, dict):
            logger.warning(f"Skipping non-dict entry at index {idx}")
            continue
        try:
            validated.append(LlmSentence(**item))
        except Exception as e:
            logger.warning(f"Validation failed for sentence {idx}: {e}")
            raise LlmInvalidResponse(f"Invalid sentence at index {idx}: {e}")
    return validated


def validate_evaluate_response(raw: Any) -> LlmEvaluateResponse:
    """Валидирует ответ evaluate_translation через Pydantic."""
    if not isinstance(raw, dict):
        raise LlmInvalidResponse(f"Expected dict, got {type(raw)}")
    try:
        return LlmEvaluateResponse(**raw)
    except Exception as e:
        logger.warning(f"Evaluate response validation failed: {e}")
        raise LlmInvalidResponse(f"Invalid evaluate response: {e}")


# ──────────────────────────────────────────────
# Токен-менеджер (один на процесс)
# ──────────────────────────────────────────────

class GigaTokenManager:
    """
    Менеджер токенов GigaChat.
    Хранит токен в памяти, обновляет по необходимости.
    Использует asyncio.Lock для single-flight refresh.
    """

    def __init__(self):
        self._access_token: str | None = None
        self._expires_at: datetime | None = None
        self._lock = asyncio.Lock()

    @property
    def is_valid(self) -> bool:
        if not self._access_token or not self._expires_at:
            return False
        return datetime.now(timezone.utc) < self._expires_at - timedelta(seconds=30)

    async def get_token(self, force_refresh: bool = False) -> str:
        if not force_refresh and self.is_valid:
            return self._access_token
        async with self._lock:
            if not force_refresh and self.is_valid:
                return self._access_token
            await self._refresh()
            return self._access_token

    async def _refresh(self) -> None:
        rq_uid = str(uuid.uuid4())
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        headers = {
            "Authorization": f"Basic {settings.GIGACHAT_AUTH_KEY}",
            "RqUID": rq_uid,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        data = {"scope": settings.GIGACHAT_SCOPE}

        if settings.GIGACHAT_VERIFY_SSL:
            ssl_context = ssl.create_default_context()
        else:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            logger.warning("SSL verification disabled for GigaChat OAuth")

        logger.debug(
            "GigaChat OAuth request: url=%s, rq_uid=%s, scope=%s",
            url, rq_uid, settings.GIGACHAT_SCOPE,
        )

        try:
            async with httpx.AsyncClient(verify=ssl_context, timeout=10.0) as client:
                resp = await client.post(url, headers=headers, data=data)
                logger.debug("GigaChat OAuth response: status=%s", resp.status_code)
                if resp.status_code != 200:
                    logger.error(
                        "GigaChat OAuth error: status=%s, body=%s",
                        resp.status_code, resp.text[:500],
                    )
                    resp.raise_for_status()
                payload = resp.json()
                self._access_token = payload["access_token"]
                expires_at_ts = payload.get("expires_at")
                if expires_at_ts:
                    self._expires_at = datetime.fromtimestamp(
                        expires_at_ts / 1000, tz=timezone.utc
                    )
                else:
                    self._expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
                logger.info("GigaChat token refreshed, expires at %s", self._expires_at)
        except Exception as e:
            logger.critical("Failed to refresh GigaChat token: %s", e)
            raise LlmUnavailable(f"Token refresh failed: {e}")


token_manager = GigaTokenManager()


async def token_refresh_loop() -> None:
    interval = settings.GIGACHAT_TOKEN_REFRESH_MINUTES * 60
    while True:
        await asyncio.sleep(interval)
        try:
            await token_manager.get_token(force_refresh=True)
            logger.debug("Background GigaChat token refresh completed")
        except Exception as e:
            logger.critical("Background GigaChat token refresh failed: %s", e)


# ──────────────────────────────────────────────
# Слой A: chat()
# ──────────────────────────────────────────────

class GigaChatClient:
    """
    Клиент GigaChat с двумя слоями:
    - Слой A: chat() — сырой вызов API
    - Слой B: chat_json() — извлечение и валидация JSON
    """

    def __init__(self):
        self._semaphore = asyncio.Semaphore(settings.GIGACHAT_MAX_CONCURRENCY)

    async def chat(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int = 2048,
        timeout: float = 25.0,
        deadline: float | None = None,
    ) -> dict:
        logger.debug(
            "GigaChat chat request: messages=%d, temperature=%.2f, max_tokens=%d",
            len(messages), temperature, max_tokens,
        )
        async with self._semaphore:
            return await self._chat_with_retries(
                messages, temperature, max_tokens, timeout, deadline
            )

    async def _chat_with_retries(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        timeout: float,
        deadline: float | None,
    ) -> dict:
        transport_retries = 0
        max_transport_retries = 2
        while True:
            if deadline:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise LlmUnavailable("Deadline exceeded")
                timeout = min(timeout, remaining)
                if remaining < 5 and transport_retries > 0:
                    raise LlmUnavailable("Deadline too close for retry")
            try:
                token = await token_manager.get_token()
                result = await self._make_request(
                    token, messages, temperature, max_tokens, timeout
                )
                return result
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                logger.error(
                    "GigaChat HTTP error: status=%s, body=%s",
                    status_code, e.response.text[:500],
                )
                if status_code == 401:
                    if transport_retries == 0:
                        transport_retries += 1
                        logger.warning("GigaChat 401, refreshing token and retrying")
                        try:
                            await token_manager.get_token(force_refresh=True)
                            continue
                        except Exception:
                            raise LlmUnavailable("Token refresh failed after 401")
                    else:
                        logger.critical("GigaChat 401 after token refresh")
                        raise LlmUnavailable("GigaChat auth failed")
                elif status_code == 404:
                    logger.critical(
                        "GigaChat 404: url=%s, body=%s",
                        e.request.url, e.response.text[:500],
                    )
                    raise LlmUnavailable("GigaChat endpoint not found (404)")
                elif status_code == 429:
                    if transport_retries >= max_transport_retries:
                        raise LlmUnavailable("Rate limited after retries")
                    transport_retries += 1
                    retry_after = e.response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else (1.0 if transport_retries == 1 else 2.0)
                    delay += random.uniform(0, 0.5)
                    logger.warning("GigaChat 429, retrying after %.2fs", delay)
                    await asyncio.sleep(delay)
                    continue
                elif status_code == 402:
                    logger.critical("GigaChat quota exceeded (402)")
                    raise LlmQuotaExceeded()
                elif status_code == 400:
                    logger.critical("GigaChat 400: %s", e.response.text[:500])
                    raise LlmUnavailable("Bad request to GigaChat")
                elif 500 <= status_code < 600:
                    if transport_retries >= max_transport_retries:
                        raise LlmUnavailable(f"Server error {status_code}")
                    transport_retries += 1
                    delay = 1.0 * transport_retries + random.uniform(0, 0.5)
                    logger.warning("GigaChat %d, retrying after %.2fs", status_code, delay)
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.critical("Unexpected HTTP %d", status_code)
                    raise LlmUnavailable(f"Unexpected HTTP {status_code}")
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                if transport_retries >= max_transport_retries:
                    raise LlmUnavailable(f"Connection error: {e}")
                transport_retries += 1
                delay = 1.0 * transport_retries + random.uniform(0, 0.5)
                logger.warning("GigaChat connection error, retrying after %.2fs", delay)
                await asyncio.sleep(delay)
                continue

    async def _make_request(
        self,
        token: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        timeout: float,
    ) -> dict:
        url = "https://api.giga.chat/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "101slovo/1.0",
        }
        payload = {
            "model": settings.GIGACHAT_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if settings.GIGACHAT_VERIFY_SSL:
            ssl_context = ssl.create_default_context()
        else:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            logger.warning("SSL verification disabled for GigaChat API")

        logger.debug(
            "GigaChat API request: url=%s, model=%s, messages=%d",
            url, settings.GIGACHAT_MODEL, len(messages),
        )

        async with httpx.AsyncClient(verify=ssl_context, timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            logger.debug(
                "GigaChat API response: status=%s, content_length=%d",
                resp.status_code, len(resp.text),
            )
            if resp.status_code != 200:
                logger.error(
                    "GigaChat API error: status=%s, body=%s",
                    resp.status_code, resp.text[:500],
                )
                resp.raise_for_status()
            return resp.json()


# ──────────────────────────────────────────────
# Слой B: chat_json()
# ──────────────────────────────────────────────

    async def chat_json(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int = 2048,
        timeout: float = 25.0,
        deadline: float | None = None,
        max_content_retries: int = 2,
        db: Any = None,
        log_context: dict | None = None,
    ) -> dict:
        content_retries = 0
        attempt = 0
        while True:
            attempt += 1
            start_time = time.monotonic()
            try:
                raw_response = await self.chat(
                    messages, temperature, max_tokens, timeout, deadline
                )
                latency_ms = int((time.monotonic() - start_time) * 1000)

                choices = raw_response.get("choices", [])
                if not choices:
                    raise LlmInvalidResponse("No choices in response")
                finish_reason = choices[0].get("finish_reason", "")
                content = choices[0].get("message", {}).get("content", "")

                logger.debug(
                    "LLM raw response: finish_reason=%s, content_length=%d",
                    finish_reason, len(content),
                )

                if finish_reason == "length":
                    content_retries += 1
                    logger.warning("Response truncated (length), retry %d", content_retries)
                    if content_retries > max_content_retries:
                        raise LlmInvalidResponse("Response truncated (length)")
                    continue
                elif finish_reason == "blacklist":
                    raise LlmRefused("Content blocked by blacklist")

                logger.debug("Extracting JSON from content (first 100 chars): %s", content[:100])
                try:
                    parsed_json = self._extract_json(content)
                    logger.debug("JSON extracted successfully, type=%s", type(parsed_json).__name__)
                except Exception as e:
                    logger.warning("Failed to extract JSON: %s, content: %s", e, content[:500])
                    raise

                if db and log_context:
                    await log_llm_call(
                        db,
                        purpose=log_context.get("purpose", "generate"),
                        user_id=log_context.get("user_id"),
                        lesson_id=log_context.get("lesson_id"),
                        exercise_id=log_context.get("exercise_id"),
                        attempt=attempt,
                        request={"messages": messages, "temperature": temperature},
                        response_raw=content,
                        response_json=parsed_json,
                        status="ok",
                        http_status=200,
                        latency_ms=latency_ms,
                        prompt_tokens=raw_response.get("usage", {}).get("prompt_tokens"),
                        completion_tokens=raw_response.get("usage", {}).get("completion_tokens"),
                        error_code=None,
                    )
                return parsed_json

            except (LlmInvalidResponse, json.JSONDecodeError) as e:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                content_retries += 1
                logger.warning("JSON parse error: %s, retry %d", e, content_retries)
                if db and log_context:
                    await log_llm_call(
                        db,
                        purpose=log_context.get("purpose", "generate"),
                        user_id=log_context.get("user_id"),
                        lesson_id=log_context.get("lesson_id"),
                        exercise_id=log_context.get("exercise_id"),
                        attempt=attempt,
                        request={"messages": messages, "temperature": temperature},
                        response_raw=str(e),
                        response_json=None,
                        status="invalid_json",
                        http_status=None,
                        latency_ms=latency_ms,
                        prompt_tokens=None,
                        completion_tokens=None,
                        error_code="invalid_json",
                    )
                if content_retries > max_content_retries:
                    raise LlmInvalidResponse(
                        f"Failed to parse JSON after {max_content_retries} retries"
                    )
                if deadline and deadline - time.monotonic() < 5:
                    raise LlmInvalidResponse("Deadline too close for content retry")
                continue

            except (LlmUnavailable, LlmQuotaExceeded, LlmRefused):
                latency_ms = int((time.monotonic() - start_time) * 1000)
                if db and log_context:
                    await log_llm_call(
                        db,
                        purpose=log_context.get("purpose", "generate"),
                        user_id=log_context.get("user_id"),
                        lesson_id=log_context.get("lesson_id"),
                        exercise_id=log_context.get("exercise_id"),
                        attempt=attempt,
                        request={"messages": messages, "temperature": temperature},
                        response_raw=None,
                        response_json=None,
                        status="http_error",
                        http_status=None,
                        latency_ms=latency_ms,
                        prompt_tokens=None,
                        completion_tokens=None,
                        error_code="llm_error",
                    )
                raise

    def _extract_json(self, text: str) -> dict:
        logger.debug("_extract_json: input_length=%d", len(text))
        text = text.strip()

        if text.startswith("```json"):
            logger.debug("Found ```json wrapper, removing")
            text = text[7:]
        elif text.startswith("```"):
            logger.debug("Found ``` wrapper, removing")
            text = text[3:]
        if text.endswith("```"):
            logger.debug("Found closing ```, removing")
            text = text[:-3]
        text = text.strip()

        start = -1
        for i, c in enumerate(text):
            if c in ("{", "["):
                start = i
                break
        if start == -1:
            logger.debug("No JSON found in response, text after cleanup: %s", text[:500])
            raise LlmInvalidResponse("No JSON found in response")

        logger.debug("Found JSON start at position %d, char=%s", start, text[start])

        depth = 0
        for i in range(start, len(text)):
            if text[i] in ("{", "["):
                depth += 1
            elif text[i] in ("}", "]"):
                depth -= 1
            if depth == 0:
                json_str = text[start : i + 1]
                logger.debug("Found JSON end at position %d, length=%d", i, len(json_str))
                try:
                    result = json.loads(json_str)
                    logger.debug("JSON parsed successfully")
                    return result
                except json.JSONDecodeError as e:
                    logger.warning("JSON parse error: %s, json_str: %s", e, json_str[:500])
                    raise

        logger.debug("Unmatched JSON brackets")
        raise LlmInvalidResponse("Unmatched JSON brackets")


# Глобальный экземпляр клиента
llm_client = GigaChatClient()