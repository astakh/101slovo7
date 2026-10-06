"""
101slovo — Утилиты для работы с датами и стриком.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import TypedDict
from zoneinfo import ZoneInfo


class StreakResult(TypedDict):
    current: int
    longest: int
    today_done: bool


def get_user_today(user_timezone: str) -> date:
    """
    Возвращает текущую дату в часовом поясе пользователя.
    """
    tz = ZoneInfo(user_timezone)
    return datetime.now(timezone.utc).astimezone(tz).date()


def get_resets_at(user_timezone: str) -> datetime:
    """
    Возвращает UTC-время ближайшей локальной полуночи (сброс дневного лимита).
    """
    tz = ZoneInfo(user_timezone)
    now_local = datetime.now(timezone.utc).astimezone(tz)
    next_midnight_local = datetime.combine(
        now_local.date() + timedelta(days=1),
        time.min,
        tzinfo=tz,
    )
    return next_midnight_local.astimezone(timezone.utc)


def calculate_streak(dates: set[date], today: date) -> StreakResult:
    """
    Алгоритм расчёта стрика из п. 5.6 ТЗ.
    
    Даты больше today приводятся к today (остаточный риск смены пояса).
    
    Args:
        dates: Множество дат завершения уроков
        today: Текущая дата в часовом поясе пользователя
    
    Returns:
        Словарь с current (текущий стрик), longest (максимальный), today_done (занимался ли сегодня)
    """
    if not dates:
        return StreakResult(current=0, longest=0, today_done=False)

    # Приводим будущие даты к today (остаточный риск смены пояса)
    clamped_dates = {d if d <= today else today for d in dates}

    today_done = today in clamped_dates

    # Определяем anchor (начало отсчёта текущего стрика)
    if today in clamped_dates:
        anchor = today
    elif (today - timedelta(days=1)) in clamped_dates:
        anchor = today - timedelta(days=1)
    else:
        anchor = None

    # Текущий стрик
    current = 0
    if anchor:
        current = 1
        d = anchor - timedelta(days=1)
        while d in clamped_dates:
            current += 1
            d -= timedelta(days=1)

    # Максимальный стрик
    sorted_dates = sorted(clamped_dates)
    longest = 1
    current_chain = 1
    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] - sorted_dates[i - 1] == timedelta(days=1):
            current_chain += 1
        else:
            current_chain = 1
        longest = max(longest, current_chain)

    return StreakResult(current=current, longest=longest, today_done=today_done)
