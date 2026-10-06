"""
101slovo — Утилиты для детерминированного ранжирования.
Используется sha256 для воспроизводимого перемешивания слов.
"""

import hashlib


def compute_seed(profile_id: int, lesson_number: int) -> str:
    """
    Вычисляет seed для урока на основе profile_id и номера урока.
    Используется для детерминированного перемешивания.
    """
    return hashlib.sha256(f"{profile_id}:{lesson_number}".encode()).hexdigest()


def compute_rank(seed: str, word_id: int) -> str:
    """
    Вычисляет ранг слова для сортировки.
    Возвращает hex-строку для лексикографической сортировки.
    """
    return hashlib.sha256(f"{seed}:{word_id}".encode()).hexdigest()


def sort_by_rank(words: list[dict], seed: str) -> list[dict]:
    """
    Сортирует слова по возрастанию ранга.
    Детерминированная сортировка — одинаковый seed даёт одинаковый порядок.
    """
    return sorted(words, key=lambda w: compute_rank(seed, w["word_id"]))
