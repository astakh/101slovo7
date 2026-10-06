"""
101slovo — Хелперы для вызова LLM.
Удобные обёртки для Prompt 1 (генерация предложений) и Prompt 2 (оценка перевода).

Исправления:
- Исправлена логика извлечения sentences_list из ответа LLM
- Добавлено детальное логирование запроса и ответа для диагностики
"""

import json
import logging
import time
import uuid

from psycopg import AsyncConnection

from app.config import settings
from app.services.llm.gigachat import llm_client

logger = logging.getLogger(__name__)


async def generate_sentences(
    db: AsyncConnection,
    *,
    level: str,
    groups: list[dict],
    user_id: int | None = None,
    lesson_id: int | None = None,
) -> list[dict]:
    """
    Prompt 1: Генерация предложений.
    Дедлайн 45с, таймаут попытки 25с, 2 транспортных повтора, 2 контентных повтора.

    Args:
        db: Соединение с БД
        level: Уровень CEFR (A1/A2/B1/B2)
        groups: Группы слов для генерации предложений
        user_id: ID пользователя (для логирования)
        lesson_id: ID урока (для логирования)

    Returns:
        Список предложений с target_words, reference_translation и nontarget_words
    """
    logger.info("=" * 80)
    logger.info("🚀 generate_sentences() called")
    logger.info(f"Level: {level}, Groups count: {len(groups)}")
    logger.info("=" * 80)

    # Читаем промпт из БД
    cur = await db.execute(
        "SELECT system_template FROM prompts WHERE key = 'generate_sentences'"
    )
    row = await cur.fetchone()
    if row:
        system_template = row["system_template"]
        logger.info(f"✅ Loaded prompt from DB: {len(system_template)} chars")
    else:
        logger.critical("❌ prompt_missing: generate_sentences - using fallback")
        system_template = (
            "Ты лингвист-методист и составляешь учебные предложения. "
            "Для КАЖДОЙ группы слов составь ровно одно короткое предложение уровня {level}. "
            "Верни ответ СТРОГО в формате JSON-массива: "
            '[{{"group_index": 0, "sentence": "...", "reference_translation": "...", '
            '"words": [...], "nontarget_words": [...]}}]'
        )

    system_message = system_template.replace("{level}", level)

    user_message = {
        "level": level,
        "groups": groups,
    }

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": json.dumps(user_message, ensure_ascii=False)},
    ]

    logger.info(f"System message length: {len(system_message)}")
    logger.info(f"Temperature: {settings.GEN_TEMPERATURE}, Max tokens: 2048")

    deadline = time.monotonic() + 45.0

    result = await llm_client.chat_json(
        messages=messages,
        temperature=settings.GEN_TEMPERATURE,
        max_tokens=2048,
        timeout=25.0,
        deadline=deadline,
        max_content_retries=2,
        db=db,
        log_context={
            "purpose": "generate",
            "user_id": user_id,
            "lesson_id": lesson_id,
        },
    )

    logger.info(f"✅ llm_client.chat_json() completed, result type: {type(result)}")

    # ═══════════════════════════════════════════
    # ИЗВЛЕЧЕНИЕ СПИСКА ПРЕДЛОЖЕНИЙ (ИСПРАВЛЕНО!)
    # ═══════════════════════════════════════════
    sentences_list = None
    if isinstance(result, list):
        # LLM вернул JSON-массив напрямую — это нормально
        sentences_list = result
        logger.info(f"✅ LLM вернул массив напрямую, items={len(sentences_list)}")
    elif isinstance(result, dict):
        # LLM вернул объект с полем-массивом
        for key in ["sentences", "groups", "results", "exercises"]:
            if key in result and isinstance(result[key], list):
                logger.info(f"✅ Extracted list from field '{key}'")
                sentences_list = result[key]
                break
        
        if sentences_list is None:
            # Ни одно поле не найдено — оборачиваем весь dict как одно предложение
            logger.warning("⚠️ Could not extract list from dict, returning as single-item list")
            sentences_list = [result]
    else:
        # Неизвестный тип ответа
        raise ValueError(f"Unexpected LLM response type: {type(result)}")

    if not sentences_list:
        logger.warning("⚠️ sentences_list пустой после извлечения")
        return []

    # Нормализация ответа
    normalized = []
    for idx, sentence_data in enumerate(sentences_list):
        if not isinstance(sentence_data, dict):
            logger.warning(f"⚠️ Skipping non-dict entry at index {idx}")
            continue

        group_index = sentence_data.get("group_index", idx)
        reference_translation = sentence_data.get("reference_translation", "")
        sentence = sentence_data.get("sentence", "")

        # Fallback: если sentence отсутствует, но есть surface_forms
        if not sentence and "surface_forms" in sentence_data:
            surface_forms = sentence_data["surface_forms"]
            if isinstance(surface_forms, list) and surface_forms:
                sentence = " ".join(surface_forms)
                logger.warning(f"⚠️ Generated sentence from surface_forms: '{sentence}'")

        # Получаем words
        words = sentence_data.get("words", [])

        # Fallback: преобразуем surface_forms в words
        if not words and "surface_forms" in sentence_data:
            surface_forms = sentence_data["surface_forms"]
            if isinstance(surface_forms, list):
                pending_group = next(
                    (g for g in groups if g.get("group_index") == group_index), None
                )
                if pending_group and "words" in pending_group:
                    words = []
                    for i, surface_form in enumerate(surface_forms):
                        if i < len(pending_group["words"]):
                            word_data = pending_group["words"][i]
                            words.append({
                                "word_id": word_data.get("word_id"),
                                "lemma": word_data.get("lemma", ""),
                                "pos": word_data.get("pos", ""),
                                "surface_form": surface_form,
                            })

        # Извлекаем nontarget_words
        nontarget_words = sentence_data.get("nontarget_words", [])
        if not isinstance(nontarget_words, list):
            nontarget_words = []

        normalized_entry = {
            "group_index": group_index,
            "sentence": sentence,
            "reference_translation": reference_translation,
            "words": words,
            "nontarget_words": nontarget_words,
        }
        normalized.append(normalized_entry)

    logger.info(f"✅ Normalized {len(normalized)} entries")
    return normalized


async def evaluate_translation(
    db: AsyncConnection,
    *,
    target_sentence: str,
    reference_translation: str,
    target_words: list[dict],
    nontarget_words: list[dict] | None = None,
    user_translation: str,
    user_id: int | None = None,
    lesson_id: int | None = None,
    exercise_id: int | None = None,
) -> dict:
    """
    Prompt 2: Оценка перевода.
    Дедлайн 15с, таймаут попытки 10с, 1 транспортный повтор, 1 контентный повтор.

    Изменения:
    - Добавлено детальное логирование запроса и ответа для диагностики
      ложных ошибок перевода нецелевых слов

    Args:
        db: Соединение с БД
        target_sentence: Исходное предложение на английском
        reference_translation: Эталонный перевод на русский
        target_words: Список целевых слов для оценки
        nontarget_words: Список нецелевых слов для проверки ошибок перевода
        user_translation: Перевод пользователя
        user_id: ID пользователя (для логирования)
        lesson_id: ID урока (для логирования)
        exercise_id: ID упражнения (для логирования)

    Returns:
        Словарь с оценками, suggested_words и translation_errors
    """
    # ═══════════════════════════════════════════
    # ЛОГИРОВАНИЕ: входные данные запроса
    # ═══════════════════════════════════════════
    logger.info(f"[evaluate_translation] ═══════════════════════════════════")
    logger.info(f"[evaluate_translation] exercise_id={exercise_id}")
    logger.info(f"[evaluate_translation] target_sentence='{target_sentence}'")
    logger.info(f"[evaluate_translation] reference_translation='{reference_translation}'")
    logger.info(f"[evaluate_translation] user_translation='{user_translation}'")
    logger.info(f"[evaluate_translation] target_words count={len(target_words)}")
    logger.info(f"[evaluate_translation] nontarget_words count={len(nontarget_words or [])}")

    if nontarget_words:
        for nt in nontarget_words:
            logger.info(
                f"[evaluate_translation]   nontarget: word_id={nt.get('word_id')}, "
                f"lemma='{nt.get('lemma')}', translations={nt.get('correct_translations', [])}"
            )

    # Читаем промпт из БД
    cur = await db.execute(
        "SELECT system_template FROM prompts WHERE key = 'evaluate_translation'"
    )
    row = await cur.fetchone()
    if row:
        system_message = row["system_template"]
        logger.info(f"[evaluate_translation] Loaded prompt from DB: {len(system_message)} chars")
    else:
        logger.critical("[evaluate_translation] prompt_missing: evaluate_translation")
        system_message = "Ты строгий экзаменатор. Оцени перевод."

    # Генерируем случайный разделитель для защиты от prompt-injection
    separator = f"<<<UT_{uuid.uuid4().hex[:8]}>>>"
    wrapped_translation = f"{separator}{user_translation}{separator}"

    user_message = {
        "target_sentence": target_sentence,
        "reference_translation": reference_translation,
        "target_words": target_words,
        "allowed_pos": [
            "noun", "verb", "adj", "adv",
            "pron", "prep", "conj", "num", "det", "intj",
        ],
        "user_translation": wrapped_translation,
    }

    # Добавляем нецелевые слова в запрос к LLM
    if nontarget_words:
        user_message["nontarget_words"] = nontarget_words
    else:
        user_message["nontarget_words"] = []

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": json.dumps(user_message, ensure_ascii=False)},
    ]

    logger.info(f"[evaluate_translation] Request user_message size: {len(json.dumps(user_message, ensure_ascii=False))} chars")

    deadline = time.monotonic() + 15.0

    result = await llm_client.chat_json(
        messages=messages,
        temperature=settings.EVAL_TEMPERATURE,
        max_tokens=1024,
        timeout=10.0,
        deadline=deadline,
        max_content_retries=1,
        db=db,
        log_context={
            "purpose": "evaluate",
            "user_id": user_id,
            "lesson_id": lesson_id,
            "exercise_id": exercise_id,
        },
    )

    # ═══════════════════════════════════════════
    # ЛОГИРОВАНИЕ: ответ LLM
    # ═══════════════════════════════════════════
    logger.info(f"[evaluate_translation] ═══════════════════════════════════")
    logger.info(f"[evaluate_translation] LLM response received:")
    logger.info(f"[evaluate_translation]   evaluations={json.dumps(result.get('evaluations', []), ensure_ascii=False)}")
    logger.info(f"[evaluate_translation]   new_suggested_words={json.dumps(result.get('new_suggested_words', []), ensure_ascii=False)}")
    logger.info(f"[evaluate_translation]   translation_errors={json.dumps(result.get('translation_errors', []), ensure_ascii=False)}")

    # Детальное логирование каждой ошибки перевода
    translation_errors = result.get("translation_errors", [])
    if translation_errors:
        logger.warning(f"[evaluate_translation] ⚠️ LLM вернул {len(translation_errors)} ошибок перевода:")
        for i, err in enumerate(translation_errors):
            logger.warning(
                f"[evaluate_translation]   ошибка[{i}]: word_id={err.get('word_id')}, "
                f"user_fragment='{err.get('user_fragment')}', "
                f"correct_translation='{err.get('correct_translation')}'"
            )
    else:
        logger.info(f"[evaluate_translation] ✅ LLM не вернул ошибок перевода")

    return result