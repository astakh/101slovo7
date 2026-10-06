"""
101slovo — Тесты алгоритма стрика (п. 5.6 ТЗ).
"""

import pytest
from datetime import date
from app.utils.datetime import calculate_streak


class TestCalculateStreak:
    """Тесты функции calculate_streak для всех случаев из п. 5.6 ТЗ."""

    TODAY = date(2026, 1, 10)

    @pytest.mark.parametrize(
        "dates_str,expected_current,expected_longest",
        [
            ([], 0, 0),  # Нет занятий
            (["2026-01-10"], 1, 1),  # Сегодня
            (["2026-01-09"], 1, 1),  # Вчера (под угрозой)
            (["2026-01-08"], 0, 1),  # Позавчера (стрик прерван)
            (
                ["2026-01-07", "2026-01-08", "2026-01-09", "2026-01-10"],
                4,
                4,
            ),  # 4 дня подряд
            (
                ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-09", "2026-01-10"],
                2,
                3,
            ),  # Пропуск 8-го
            (["2026-01-09", "2026-01-11"], 2, 2),  # Будущая дата приводится к today
        ],
    )
    def test_calculate_streak(self, dates_str, expected_current, expected_longest):
        """Тест всех случаев из п. 5.6 ТЗ."""
        dates = {date.fromisoformat(d) for d in dates_str}
        result = calculate_streak(dates, self.TODAY)
        assert result["current"] == expected_current, f"dates={dates_str}"
        assert result["longest"] == expected_longest, f"dates={dates_str}"

    def test_streak_today_done(self):
        """Проверка флага today_done."""
        # Сегодня занимался
        dates = {date(2026, 1, 10)}
        result = calculate_streak(dates, self.TODAY)
        assert result["today_done"] is True

        # Сегодня не занимался
        dates = {date(2026, 1, 9)}
        result = calculate_streak(dates, self.TODAY)
        assert result["today_done"] is False

    def test_streak_future_dates(self):
        """Проверка приведения будущих дат к today."""
        # Будущая дата должна приводиться к today
        dates = {date(2026, 1, 15)}  # Будущее
        result = calculate_streak(dates, self.TODAY)
        assert result["current"] == 1
        assert result["today_done"] is True

    def test_streak_empty(self):
        """Проверка пустого множества дат."""
        result = calculate_streak(set(), self.TODAY)
        assert result["current"] == 0
        assert result["longest"] == 0
        assert result["today_done"] is False

    def test_streak_long_chain(self):
        """Проверка длинной цепочки."""
        # 10 дней подряд
        dates = {date(2026, 1, i) for i in range(1, 11)}
        result = calculate_streak(dates, self.TODAY)
        assert result["current"] == 10
        assert result["longest"] == 10
