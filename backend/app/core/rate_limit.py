"""
101slovo — In-memory Rate Limiter.
Защита от брутфорса на эндпоинтах auth.
Ограничения хранятся в памяти процесса (согласно ТЗ MVP).
"""

from collections import defaultdict
from fastapi import HTTPException, status


class MemoryRateLimiter:
    """
    Простой rate limiter на основе скользящего окна.
    
    - IP limit: 10 запросов в минуту (защита от массовых запросов)
    - Email limit: 5 неудачных попыток за 15 минут (защита от брутфорса)
    - Evaluate limit: 30 запросов в минуту на пользователя
    - Report limit: 20 жалоб в час на пользователя
    """

    def __init__(self):
        self._ip_attempts: dict[str, list[float]] = defaultdict(list)
        self._email_failures: dict[str, list[float]] = defaultdict(list)
        self._evaluate_attempts: dict[int, list[float]] = defaultdict(list)
        self._report_attempts: dict[int, list[float]] = defaultdict(list)

    def check_ip_limit(self, ip: str) -> None:
        """
        Проверка лимита по IP.
        Максимум 10 запросов в минуту.
        """
        now = __import__("time").time()
        window = 60  # 1 минута
        max_attempts = 10

        # Очистка старых записей
        self._ip_attempts[ip] = [
            t for t in self._ip_attempts[ip] if now - t < window
        ]

        if len(self._ip_attempts[ip]) >= max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="too_many_requests",
            )

        self._ip_attempts[ip].append(now)

    def check_email_limit(self, email: str) -> None:
        """
        Проверка лимита неудачных попыток по email.
        Максимум 5 неудач за 15 минут.
        """
        now = __import__("time").time()
        window = 900  # 15 минут
        max_failures = 5

        # Очистка старых записей
        self._email_failures[email] = [
            t for t in self._email_failures[email] if now - t < window
        ]

        if len(self._email_failures[email]) >= max_failures:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="too_many_failed_attempts",
            )

    def record_failure(self, email: str) -> None:
        """Запись неудачной попытки входа."""
        now = __import__("time").time()
        self._email_failures[email].append(now)

    def check_evaluate_limit(self, user_id: int) -> None:
        """
        Проверка лимита запросов оценки упражнения.
        Максимум 30 запросов в минуту на пользователя.
        """
        now = __import__("time").time()
        window = 60  # 1 минута
        max_attempts = 30

        # Очистка старых записей
        self._evaluate_attempts[user_id] = [
            t for t in self._evaluate_attempts[user_id] if now - t < window
        ]

        if len(self._evaluate_attempts[user_id]) >= max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="too_many_requests",
            )

        self._evaluate_attempts[user_id].append(now)

    def check_report_limit(self, user_id: int) -> None:
        """
        Проверка лимита жалоб на предложения.
        Максимум 20 жалоб в час на пользователя.
        """
        now = __import__("time").time()
        window = 3600  # 1 час
        max_attempts = 20

        # Очистка старых записей
        self._report_attempts[user_id] = [
            t for t in self._report_attempts[user_id] if now - t < window
        ]

        if len(self._report_attempts[user_id]) >= max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="too_many_reports",
            )

        self._report_attempts[user_id].append(now)

    def cleanup(self) -> None:
        """
        Очистка устаревших записей.
        Рекомендуется вызывать периодически (например, раз в час).
        """
        now = __import__("time").time()
        
        # Очистка IP записей старше 1 минуты
        expired_ips = [
            ip for ip, timestamps in self._ip_attempts.items()
            if all(now - t >= 60 for t in timestamps)
        ]
        for ip in expired_ips:
            del self._ip_attempts[ip]

        # Очистка email записей старше 15 минут
        expired_emails = [
            email for email, timestamps in self._email_failures.items()
            if all(now - t >= 900 for t in timestamps)
        ]
        for email in expired_emails:
            del self._email_failures[email]


# Глобальный экземпляр limiter
limiter = MemoryRateLimiter()
