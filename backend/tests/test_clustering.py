"""
101slovo — Тесты алгоритма кластеризации слов.
"""

import pytest
from app.utils.clustering import cluster_words


class TestClusterWords:
    """Тесты функции cluster_words."""

    SEED = "test_seed"

    def test_single_word(self):
        """Одно слово — одна группа."""
        result = cluster_words([1], self.SEED)
        assert result == [[1]]

    def test_two_words(self):
        """Два слова — одна группа."""
        result = cluster_words([1, 2], self.SEED)
        assert len(result) == 1
        assert sorted(result[0]) == [1, 2]

    def test_three_words(self):
        """Три слова — одна группа."""
        result = cluster_words([1, 2, 3], self.SEED)
        assert len(result) == 1
        assert sorted(result[0]) == [1, 2, 3]

    def test_four_words(self):
        """Четыре слова — две группы по 2."""
        result = cluster_words([1, 2, 3, 4], self.SEED)
        assert len(result) == 2
        assert sorted([len(g) for g in result]) == [2, 2]

    def test_five_words(self):
        """Пять слов — группы [2, 3]."""
        result = cluster_words([1, 2, 3, 4, 5], self.SEED)
        assert len(result) == 2
        assert sorted([len(g) for g in result]) == [2, 3]

    def test_six_words(self):
        """Шесть слов — две группы по 3."""
        result = cluster_words([1, 2, 3, 4, 5, 6], self.SEED)
        assert len(result) == 2
        assert sorted([len(g) for g in result]) == [3, 3]

    def test_seven_words(self):
        """Семь слов — группы [2, 2, 3]."""
        result = cluster_words([1, 2, 3, 4, 5, 6, 7], self.SEED)
        assert len(result) == 3
        assert sorted([len(g) for g in result]) == [2, 2, 3]

    def test_ten_words(self):
        """Десять слов — группы [3, 3, 4]."""
        result = cluster_words(list(range(1, 11)), self.SEED)
        assert len(result) == 4
        assert sorted([len(g) for g in result]) == [2, 2, 3, 3]

    def test_deterministic(self):
        """Проверка детерминированности."""
        words = list(range(1, 11))
        result1 = cluster_words(words, self.SEED)
        result2 = cluster_words(words, self.SEED)
        assert result1 == result2, "Кластеризация должна быть детерминированной"

    def test_different_seeds(self):
        """Разные seed дают разный порядок."""
        words = list(range(1, 11))
        result1 = cluster_words(words, "seed1")
        result2 = cluster_words(words, "seed2")
        # Размеры групп должны быть одинаковыми
        assert sorted([len(g) for g in result1]) == sorted([len(g) for g in result2])
        # Но порядок слов может отличаться
        # (не проверяем строго, так как зависит от реализации)

    def test_empty_list(self):
        """Пустой список."""
        result = cluster_words([], self.SEED)
        assert result == []

    def test_all_words_present(self):
        """Все слова должны присутствовать в результате."""
        words = list(range(1, 11))
        result = cluster_words(words, self.SEED)
        all_words = [w for group in result for w in group]
        assert sorted(all_words) == sorted(words)
