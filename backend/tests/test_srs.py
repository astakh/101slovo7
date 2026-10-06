"""
101slovo — Тесты алгоритма SRS (п. 5.1 ТЗ).
"""

import pytest
from app.services.srs import srs_update


class TestSRSUpdate:
    """Тесты функции srs_update для всех случаев из п. 5.1 ТЗ."""

    LESSON_NUMBER = 10

    @pytest.mark.parametrize(
        "stage,result,expected_stage,expected_due,expected_status",
        [
            # Правильные ответы
            (0, "correct", 1, 11, "active"),
            (1, "correct", 2, 12, "active"),
            (2, "correct", 3, 13, "active"),
            (3, "correct", 4, 17, "active"),
            (4, "correct", 5, 21, "active"),
            (5, "correct", 6, 40, "active"),
            (6, "correct", 6, None, "mastered"),  # Запомнено
            # Опечатки (как правильные)
            (0, "typo", 1, 11, "active"),
            (1, "typo", 2, 12, "active"),
            (2, "typo", 3, 13, "active"),
            (3, "typo", 4, 17, "active"),
            (4, "typo", 5, 21, "active"),
            (5, "typo", 6, 40, "active"),
            (6, "typo", 6, None, "mastered"),  # Запомнено
            # Неправильные ответы
            (0, "incorrect", 0, 11, "active"),  # min(stage-1, 0) = 0
            (1, "incorrect", 0, 11, "active"),
            (2, "incorrect", 1, 11, "active"),
            (3, "incorrect", 2, 12, "active"),
            (4, "incorrect", 3, 13, "active"),
            (5, "incorrect", 4, 17, "active"),
            (6, "incorrect", 5, 21, "active"),
        ],
    )
    def test_srs_update(
        self, stage, result, expected_stage, expected_due, expected_status
    ):
        """Тест всех случаев из п. 5.1 ТЗ."""
        new_stage, due, status = srs_update(stage, result, self.LESSON_NUMBER)
        assert new_stage == expected_stage, f"stage={stage}, result={result}"
        assert due == expected_due, f"stage={stage}, result={result}"
        assert status == expected_status, f"stage={stage}, result={result}"

    def test_srs_intervals(self):
        """Проверка интервалов повторения."""
        # Интервалы: [1, 2, 3, 7, 11, 30]
        # Для stage=0 (после correct → stage=1): interval[0] = 1
        _, due, _ = srs_update(0, "correct", 10)
        assert due == 11  # 10 + 1

        # Для stage=5 (после correct → stage=6): interval[5] = 30
        _, due, _ = srs_update(5, "correct", 10)
        assert due == 40  # 10 + 30

    def test_srs_max_stage(self):
        """Проверка максимальной стадии (mastered)."""
        new_stage, due, status = srs_update(6, "correct", 10)
        assert new_stage == 6
        assert due is None
        assert status == "mastered"

    def test_srs_min_stage(self):
        """Проверка минимальной стадии (0)."""
        new_stage, due, status = srs_update(0, "incorrect", 10)
        assert new_stage == 0
        assert due == 11
        assert status == "active"
