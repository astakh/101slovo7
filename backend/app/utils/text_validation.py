"""
101slovo — Утилиты валидации текста.
Нормализация и проверка пользовательского ввода.
"""

import re
import unicodedata


def validate_user_translation(text: str) -> str:
    """
    Валидация ввода пользователя по п. 5.5 шаг 4.
    Возвращает нормализованный текст или бросает ValueError.
    
    Правила:
    1. NFC нормализация
    2. Trim пробелов
    3. Схлопывание множественных пробелов
    4. Длина 1-500 символов
    5. Удаление управляющих символов (кроме \n и \t)
    6. Удаление последовательностей <<< и >>> (защита от prompt injection)
    """
    # 1. NFC
    text = unicodedata.normalize("NFC", text)
    # 2. trim
    text = text.strip()
    # 3. Схлопывание пробелов
    text = re.sub(r"\s+", " ", text)
    # 4. Длина 1-500
    if len(text) < 1 or len(text) > 500:
        raise ValueError("invalid_length")
    # 5. Удаление управляющих символов
    text = "".join(c for c in text if unicodedata.category(c)[0] != "C" or c in "\n\t")
    # 6. Удаление последовательностей <<< и >>>
    text = text.replace("<<<", "").replace(">>>", "")

    return text


def compute_lemma_key(lemma: str) -> str:
    """
    Вычисляет нормализованный ключ леммы: casefold(NFC(trim(lemma))).
    Используется для поиска и сравнения слов.
    """
    normalized = unicodedata.normalize("NFC", lemma.strip())
    return normalized.casefold()


def normalize_for_comparison(text: str) -> str:
    """
    Нормализует текст для сравнения фрагментов.
    NFC + lower + схлопывание пробелов.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def validate_user_fragment(user_input: str, fragment: str | None) -> str | None:
    """
    Проверяет, что фрагмент является подстрокой ввода пользователя.
    Возвращает оригинальный fragment если найден, иначе None.
    """
    if fragment is None:
        return None

    normalized_input = normalize_for_comparison(user_input)
    normalized_fragment = normalize_for_comparison(fragment)

    if normalized_fragment in normalized_input:
        return fragment
    return None
