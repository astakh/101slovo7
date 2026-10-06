"""
101slovo — Тесты валидации текста.
"""

import pytest
from app.utils.text_validation import (
    validate_user_translation,
    compute_lemma_key,
    normalize_for_comparison,
    validate_user_fragment,
)


class TestValidateUserTranslation:
    """Тесты функции validate_user_translation."""

    def test_trim_spaces(self):
        """Обрезка пробелов."""
        assert validate_user_translation("  hello world  ") == "hello world"

    def test_collapse_spaces(self):
        """Схлопывание множественных пробелов."""
        assert validate_user_translation("hello   world") == "hello world"

    def test_max_length(self):
        """Максимальная длина 500."""
        text = "a" * 500
        assert validate_user_translation(text) == text

    def test_too_long(self):
        """Слишком длинный текст."""
        with pytest.raises(ValueError):
            validate_user_translation("a" * 501)

    def test_empty(self):
        """Пустой текст."""
        with pytest.raises(ValueError):
            validate_user_translation("")

    def test_whitespace_only(self):
        """Только пробелы."""
        with pytest.raises(ValueError):
            validate_user_translation("   ")

    def test_remove_control_chars(self):
        """Удаление управляющих символов."""
        result = validate_user_translation("hello\x00world")
        assert "\x00" not in result
        assert result == "helloworld"

    def test_keep_newline_tab(self):
        """Сохранение \\n и \\t."""
        result = validate_user_translation("hello\nworld\ttest")
        assert "\n" in result
        assert "\t" in result

    def test_remove_injection(self):
        """Удаление последовательностей <<< и >>>."""
        result = validate_user_translation("hello <<<script>>> world")
        assert "<<<" not in result
        assert ">>>" not in result
        assert result == "hello script world"

    def test_nfc_normalization(self):
        """NFC нормализация Unicode."""
        # é может быть представлено как один символ или два
        text1 = "café"  # один символ é
        text2 = "cafe\u0301"  # e + combining accent
        result1 = validate_user_translation(text1)
        result2 = validate_user_translation(text2)
        assert result1 == result2


class TestComputeLemmaKey:
    """Тесты функции compute_lemma_key."""

    def test_lowercase(self):
        """Приведение к нижнему регистру."""
        assert compute_lemma_key("RUN") == "run"
        assert compute_lemma_key("Running") == "running"

    def test_trim(self):
        """Обрезка пробелов."""
        assert compute_lemma_key("  run  ") == "run"

    def test_casefold(self):
        """Casefold для Unicode."""
        assert compute_lemma_key("DON'T") == "don't"
        assert compute_lemma_key("Straße") == "straße"

    def test_nfc(self):
        """NFC нормализация."""
        key1 = compute_lemma_key("café")
        key2 = compute_lemma_key("cafe\u0301")
        assert key1 == key2


class TestNormalizeForComparison:
    """Тесты функции normalize_for_comparison."""

    def test_lowercase(self):
        """Приведение к нижнему регистру."""
        assert normalize_for_comparison("HELLO") == "hello"

    def test_collapse_spaces(self):
        """Схлопывание пробелов."""
        assert normalize_for_comparison("hello   world") == "hello world"

    def test_trim(self):
        """Обрезка пробелов."""
        assert normalize_for_comparison("  hello  ") == "hello"


class TestValidateUserFragment:
    """Тесты функции validate_user_fragment."""

    def test_fragment_found(self):
        """Фрагмент найден."""
        result = validate_user_fragment("hello world", "world")
        assert result == "world"

    def test_fragment_not_found(self):
        """Фрагмент не найден."""
        result = validate_user_fragment("hello world", "xyz")
        assert result is None

    def test_case_insensitive(self):
        """Регистронезависимый поиск."""
        result = validate_user_fragment("Hello World", "WORLD")
        assert result == "WORLD"

    def test_none_fragment(self):
        """None фрагмент."""
        result = validate_user_fragment("hello world", None)
        assert result is None

    def test_spaces_normalized(self):
        """Нормализация пробелов."""
        result = validate_user_fragment("hello  world", "hello world")
        assert result == "hello world"
