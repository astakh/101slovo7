"""
101slovo — Утилиты для кластеризации слов.
Разбиение слов на группы по 1-3 слова для упражнений.
"""

import math
import random


def cluster_words(word_ids: list[int], seed: str) -> list[list[int]]:
    """
    Разбивает слова на группы по 1-3 слова.
    Размеры групп отличаются не более чем на 1.
    Меньшие группы идут первыми.
    Распределение детерминировано от seed.
    
    Args:
        word_ids: Список ID слов для кластеризации
        seed: Seed для детерминированного перемешивания
    
    Returns:
        Список групп (каждая группа — список word_id)
    
    Примеры:
        cluster_words([1], seed) -> [[1]]
        cluster_words([1,2,3,4], seed) -> [[1,2], [3,4]] (порядок зависит от seed)
        cluster_words([1,2,3,4,5], seed) -> [[1,2], [3,4,5]] (меньшие первыми)
        cluster_words([1,2,3,4,5,6,7], seed) -> [[1,2], [3,4], [5,6,7]]
    """
    N = len(word_ids)
    if N == 0:
        return []
    
    # Количество групп: ceil(N / 3)
    k = math.ceil(N / 3)
    
    # Детерминированное перемешивание
    rng = random.Random(seed)
    shuffled = word_ids.copy()
    rng.shuffle(shuffled)
    
    # Распределение по группам
    base_size = N // k
    remainder = N % k
    
    groups = []
    idx = 0
    for i in range(k):
        size = base_size + (1 if i < remainder else 0)
        groups.append(shuffled[idx:idx + size])
        idx += size
    
    # Меньшие группы первыми
    groups.sort(key=len)
    
    return groups
