"""
101slovo — Тесты валидации предложений.
"""

import pytest
from app.utils.sentence_validation import (
    find_surface_form,
    contains_cyrillic,
    normalize_sentence,
    validate_group_response,
)


class TestFindSurfaceForm:
    """Тесты функции find_surface_form."""

    def test_simple_match(self):
        """Простое совпадение."""
        result = find_surface_form("She runs fast", "runs")
        assert result == (4, 8)

    def test_not_whole_word(self):
        """Не целое слово."""
        result = find_surface_form("She runs fast", "run")
        assert result is None

    def test_apostrophe(self):
        """Апостроф как часть слова."""
        result = find_surface_form("Don't run", "don't")
        assert result == (0, 5)

    def test_hyphen(self):
        """Дефис как часть слова."""
        result = find_surface_form("well-known fact", "well-known")
        assert result == (0, 10)

    def test_case_insensitive(self):
        """Регистронезависимый поиск."""
        result = find_surface_form("She RUNS fast", "runs")
        assert result == (4, 8)

    def test_not_found(self):
        """Не найдено."""
        result = find_surface_form("She runs fast", "walks")
        assert result is None

    def test_at_start(self):
        """В начале предложения."""
        result = find_surface_form("Running is fun", "running")
        assert result == (0, 7)

    def test_at_end(self):
        """В конце предложения."""
        result = find_surface_form("I like running", "running")
        assert result == (7, 14)

    def test_empty_sentence(self):
        """Пустое предложение."""
        result = find_surface_form("", "run")
        assert result is None

    def test_empty_form(self):
        """Пустая форма."""
        result = find_surface_form("She runs", "")
        assert result is None


class TestContainsCyrillic:
    """Тесты функции contains_cyrillic."""

    def test_cyrillic_present(self):
        """Кириллица присутствует."""
        assert contains_cyrillic("Привет") is True
        assert contains_cyrillic("Hello Мир") is True

    def test_cyrillic_absent(self):
        """Кириллица отсутствует."""
        assert contains_cyrillic("Hello") is False
        assert contains_cyrillic("123 !@#") is False

    def test_empty_string(self):
        """Пустая строка."""
        assert contains_cyrillic("") is False

    def test_mixed(self):
        """Смешанный текст."""
        assert contains_cyrillic("Hello World Привет") is True
        assert contains_cyrillic("Hello World 123") is False


class TestNormalizeSentence:
    """Тесты функции normalize_sentence."""

    def test_lowercase(self):
        """Приведение к нижнему регистру."""
        assert normalize_sentence("HELLO WORLD") == "hello world"

    def test_remove_punctuation(self):
        """Удаление пунктуации."""
        assert normalize_sentence("Hello, world!") == "hello world"

    def test_collapse_spaces(self):
        """Схлопывание пробелов."""
        assert normalize_sentence("Hello   world") == "hello world"

    def test_trim(self):
        """Обрезка пробелов."""
        assert normalize_sentence("  Hello world  ") == "hello world"


class TestValidateGroupResponse:
    """Тесты функции validate_group_response."""

    def test_valid_response(self):
        """Валидный ответ."""
        requested_words = [
            {"lemma": "run", "pos": "verb"},
            {"lemma": "fast", "pos": "adv"},
        ]
        response_entry = {
            "sentence": "She runs fast every morning.",
            "reference_translation": "Она быстро бегает каждое утро.",
            "words": [
                {"lemma": "run", "pos": "verb", "surface_form": "runs"},
                {"lemma": "fast", "pos": "adv", "surface_form": "fast"},
            ],
        }
        result = validate_group_response(0, requested_words, response_entry, [])
        assert result is None

    def test_sentence_too_long(self):
        """Предложение слишком длинное."""
        requested_words = [{"lemma": "run", "pos": "verb"}]
        response_entry = {
            "sentence": "x" * 201,
            "reference_translation": "Перевод",
            "words": [{"lemma": "run", "pos": "verb", "surface_form": "x"}],
        }
        result = validate_group_response(0, requested_words, response_entry, [])
        assert result is not None
        assert "too long" in result

    def test_sentence_has_cyrillic(self):
        """Предложение содержит кириллицу."""
        requested_words = [{"lemma": "run", "pos": "verb"}]
        response_entry = {
            "sentence": "She runs Привет",
            "reference_translation": "Она бегает",
            "words": [{"lemma": "run", "pos": "verb", "surface_form": "runs"}],
        }
        result = validate_group_response(0, requested_words, response_entry, [])
        assert result is not None
        assert "Cyrillic" in result

    def test_translation_no_cyrillic(self):
        """Перевод не содержит кириллицу."""
        requested_words = [{"lemma": "run", "pos": "verb"}]
        response_entry = {
            "sentence": "She runs fast",
            "reference_translation": "She runs fast",
            "words": [{"lemma": "run", "pos": "verb", "surface_form": "runs"}],
        }
        result = validate_group_response(0, requested_words, response_entry, [])
        assert result is not None
        assert "no Cyrillic" in result

    def test_word_set_mismatch(self):
        """Несоответствие набора слов."""
        requested_words = [{"lemma": "run", "pos": "verb"}]
        response_entry = {
            "sentence": "She walks fast",
            "reference_translation": "Она ходит быстро",
            "words": [{"lemma": "walk", "pos": "verb", "surface_form": "walks"}],
        }
        result = validate_group_response(0, requested_words, response_entry, [])
        assert result is not None
        assert "mismatch" in result

    def test_surface_form_not_found(self):
        """Форма слова не найдена в предложении."""
        requested_words = [{"lemma": "run", "pos": "verb"}]
        response_entry = {
            "sentence": "She walks fast",
            "reference_translation": "Она ходит быстро",
            "words": [{"lemma": "run", "pos": "verb", "surface_form": "runs"}],
        }
        result = validate_group_response(0, requested_words, response_entry, [])
        assert result is not None
        assert "not found" in result

    def test_duplicate_sentence(self):
        """Дубликат предложения."""
        requested_words = [{"lemma": "run", "pos": "verb"}]
        response_entry = {
            "sentence": "She runs fast",
            "reference_translation": "Она бегает быстро",
            "words": [{"lemma": "run", "pos": "verb", "surface_form": "runs"}],
        }
        all_sentences = ["She runs fast every day"]
        result = validate_group_response(0, requested_words, response_entry, all_sentences)
        assert result is not None
        assert "duplicate" in result
