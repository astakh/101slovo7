"""
101slovo — Сервис оценки упражнения.
Алгоритм 5.5 из ТЗ: оценка перевода через LLM, обновление SRS,
автозавершение урока, подсказки новых слов, детекция ошибок в нецелевых словах.

Изменения (фича nontarget_words):
- Убрана ветка «Не знаю» — пользователь всегда вводит перевод
- Добавлена обработка translation_errors из ответа LLM
- Подсказки разделяются на обычные (new) и ошибки перевода (error)

Исправления:
- _build_saved_result теперь корректно возвращает lesson_completed из БД
"""

import json
import logging

from psycopg import AsyncConnection

from app.core.exceptions import LlmInvalidResponse, LlmRefused
from app.services.llm.helpers import evaluate_translation
from app.services.srs import srs_update
from app.utils.datetime import get_user_today
from app.utils.text_validation import (
    compute_lemma_key,
    normalize_for_comparison,
    validate_user_fragment,
    validate_user_translation,
)

logger = logging.getLogger(__name__)

# Лимит подсказок
MAX_REGULAR_SUGGESTIONS = 3
MAX_ERROR_SUGGESTIONS = 3


async def evaluate_exercise(
    db: AsyncConnection,
    *,
    user_id: int,
    profile_id: int,
    exercise_id: int,
    user_translation: str | None = None,
) -> dict:
    """
    Алгоритм 5.5: Проверка упражнения.
    """

    # ═══════════════════════════════════════════
    # 1. Доступ и состояние
    # ═══════════════════════════════════════════
    cur = await db.execute(
        """SELECT le.id, le.lesson_id, le.order_index, le.status, le.target_sentence,
                le.reference_translation, le.target_words, le.nontarget_words, le.user_translation,
                l.id as lesson_id, l.status as lesson_status, l.lesson_number, l.learning_profile_id
        FROM lesson_exercises le
        JOIN lessons l ON l.id = le.lesson_id
        WHERE le.id = %s""",
        [exercise_id],
    )
    exercise = await cur.fetchone()
    if not exercise:
        raise ValueError("exercise_not_found")
    if exercise["learning_profile_id"] != profile_id:
        raise ValueError("exercise_not_found")

    # ═══════════════════════════════════════════
    # 2. Идемпотентность
    # ═══════════════════════════════════════════
    if exercise["status"] == "evaluated":
        return await _build_saved_result(db, exercise_id)

    # ═══════════════════════════════════════════
    # 3. Порядок: только первое pending
    # ═══════════════════════════════════════════
    cur = await db.execute(
        """SELECT id FROM lesson_exercises
        WHERE lesson_id = %s AND status = 'pending'
        ORDER BY order_index LIMIT 1""",
        [exercise["lesson_id"]],
    )
    first_pending = await cur.fetchone()
    if not first_pending or first_pending["id"] != exercise_id:
        raise ValueError("not_current_exercise")

    # ═══════════════════════════════════════════
    # 4. Проверка статуса урока
    # ═══════════════════════════════════════════
    if exercise["lesson_status"] != "in_progress":
        raise ValueError("lesson_not_active")

    # ═══════════════════════════════════════════
    # 5. Валидация ввода
    # ═══════════════════════════════════════════
    if not user_translation:
        raise ValueError("invalid_input")
    try:
        user_translation = validate_user_translation(user_translation)
    except ValueError:
        raise ValueError("invalid_input")

    target_words = exercise["target_words"]
    word_ids = [w["word_id"] for w in target_words]
    nontarget_words = exercise.get("nontarget_words", [])

    cur = await db.execute(
        "SELECT id, lemma, lemma_key, pos, translations FROM words WHERE id = ANY(%s)",
        [word_ids],
    )
    words_data = {r["id"]: r for r in await cur.fetchall()}

    # ═══════════════════════════════════════════
    # 6. Вызов LLM (Prompt 2)
    # ═══════════════════════════════════════════
    llm_target_words = []
    for tw in target_words:
        wd = words_data.get(tw["word_id"])
        if wd:
            llm_target_words.append(
                {
                    "word_id": tw["word_id"],
                    "lemma": wd["lemma"],
                    "pos": wd["pos"],
                    "surface_form": tw["surface_form"],
                    "correct_translations": wd["translations"],
                }
            )

    llm_nontarget_words = []
    for nt in nontarget_words:
        llm_nontarget_words.append(
            {
                "word_id": nt["word_id"],
                "lemma": nt["lemma"],
                "pos": nt["pos"],
                "surface_form": nt["surface_form"],
                "correct_translations": nt.get("translations", []),
            }
        )

    try:
        llm_response = await evaluate_translation(
            db,
            target_sentence=exercise["target_sentence"],
            reference_translation=exercise["reference_translation"],
            target_words=llm_target_words,
            nontarget_words=llm_nontarget_words,
            user_translation=user_translation,
            user_id=user_id,
            lesson_id=exercise["lesson_id"],
            exercise_id=exercise_id,
        )
    except LlmRefused:
        raise ValueError("llm_refused")
    except Exception as e:
        logger.error(f"LLM evaluation failed: {e}")
        raise ValueError("llm_unavailable")

    # ═══════════════════════════════════════════
    # 7. Валидация ответа LLM
    # ═══════════════════════════════════════════
    evaluations_raw = llm_response.get("evaluations", [])
    suggested_words_raw = llm_response.get("new_suggested_words", [])
    translation_errors_raw = llm_response.get("translation_errors", [])

    response_word_ids = {e.get("word_id") for e in evaluations_raw}
    expected_word_ids = set(word_ids)
    missing_word_ids = expected_word_ids - response_word_ids
    if missing_word_ids:
        for word_id in missing_word_ids:
            evaluations_raw.append(
                {"word_id": word_id, "result": "incorrect", "user_fragment": None}
            )

    if len(evaluations_raw) != len(expected_word_ids):
        raise LlmInvalidResponse("duplicate word_id")

    evaluations = []
    for ev in evaluations_raw:
        result = ev.get("result")
        if result not in ("correct", "typo", "incorrect"):
            raise LlmInvalidResponse("invalid result")

        fragment = ev.get("user_fragment")
        validated_fragment = validate_user_fragment(user_translation, fragment)
        evaluations.append(
            {
                "word_id": ev["word_id"],
                "result": result,
                "user_fragment": validated_fragment,
            }
        )

    # ═══════════════════════════════════════════
    # 8. Обработка подсказок
    # ═══════════════════════════════════════════
    regular_suggestions = await _process_suggestions(
        db, profile_id, word_ids, suggested_words_raw
    )

    error_suggestions = await _process_error_suggestions(
        db, profile_id, nontarget_words, translation_errors_raw, user_translation
    )

    regular_word_ids = {s["word_id"] for s in regular_suggestions}
    error_word_ids = {s["word_id"] for s in error_suggestions}
    duplicates = regular_word_ids & error_word_ids
    if duplicates:
        regular_suggestions = [
            s for s in regular_suggestions if s["word_id"] not in duplicates
        ]

    all_suggestions = error_suggestions + regular_suggestions

    # ═══════════════════════════════════════════
    # 9. Транзакция записи
    # ═══════════════════════════════════════════
    lesson_number = exercise["lesson_number"]
    async with db.transaction():
        cur = await db.execute(
            "SELECT id, status FROM lessons WHERE id = %s FOR UPDATE",
            [exercise["lesson_id"]],
        )
        locked_lesson = await cur.fetchone()
        if not locked_lesson or locked_lesson["status"] != "in_progress":
            raise ValueError("lesson_not_active")

        cur = await db.execute(
            "SELECT id, status FROM lesson_exercises WHERE id = %s FOR UPDATE",
            [exercise_id],
        )
        locked_exercise = await cur.fetchone()
        if locked_exercise["status"] == "evaluated":
            return await _build_saved_result(db, exercise_id)

        updated_target_words = []
        for tw in target_words:
            wid = tw["word_id"]
            ev = next((e for e in evaluations if e["word_id"] == wid), None)
            if not ev:
                ev = {"word_id": wid, "result": "incorrect", "user_fragment": None}

            cur = await db.execute(
                """SELECT id, status, stage FROM user_words
                WHERE learning_profile_id = %s AND word_id = %s FOR UPDATE""",
                [profile_id, wid],
            )
            uw = await cur.fetchone()
            stage_after = None
            if uw and uw["status"] == "active":
                new_stage, due, new_status = srs_update(
                    uw["stage"], ev["result"], lesson_number
                )
                await db.execute(
                    """UPDATE user_words
                    SET stage = %s, due_lesson_number = %s, status = %s,
                        last_reviewed_at = now(), updated_at = now()
                    WHERE id = %s""",
                    [new_stage, due, new_status, uw["id"]],
                )
                stage_after = new_stage

            tw_copy = tw.copy()
            tw_copy["result"] = ev["result"]
            tw_copy["user_fragment"] = ev["user_fragment"]
            tw_copy["stage_after"] = stage_after
            updated_target_words.append(tw_copy)

        suggested_words_json = []
        for s in all_suggestions:
            entry = {
                "word_id": s["word_id"],
                "state": "suggested",
                "suggestion_type": s.get("suggestion_type", "new"),
            }
            if s.get("suggestion_type") == "error":
                entry["user_fragment"] = s.get("user_fragment")
                entry["correct_translation"] = s.get("correct_translation")
            suggested_words_json.append(entry)

        await db.execute(
            """UPDATE lesson_exercises
            SET user_translation = %s, dont_know = false, status = 'evaluated',
                evaluated_at = now(), target_words = %s, suggested_words = %s
            WHERE id = %s""",
            [
                user_translation,
                json.dumps(updated_target_words, ensure_ascii=False),
                json.dumps(suggested_words_json, ensure_ascii=False),
                exercise_id,
            ],
        )

        cur = await db.execute(
            """SELECT COUNT(*) as cnt FROM lesson_exercises
            WHERE lesson_id = %s AND status = 'pending'""",
            [exercise["lesson_id"]],
        )
        pending_count = (await cur.fetchone())["cnt"]
        lesson_completed = False
        if pending_count == 0:
            cur = await db.execute(
                """SELECT u.timezone FROM users u
                JOIN learning_profiles lp ON lp.user_id = u.id
                WHERE lp.id = %s""",
                [profile_id],
            )
            user_tz = (await cur.fetchone())["timezone"]
            completed_date = get_user_today(user_tz)
            await db.execute(
                """UPDATE lessons
                SET status = 'completed', completed_at = now(), completed_local_date = %s
                WHERE id = %s AND status = 'in_progress'""",
                [completed_date, exercise["lesson_id"]],
            )
            lesson_completed = True

            await db.execute(
                "INSERT INTO events (user_id, type, payload) VALUES (%s, %s, %s)",
                [user_id, "lesson_completed", json.dumps({"lesson_id": exercise["lesson_id"]})],
            )

        await db.execute(
            "INSERT INTO events (user_id, type, payload) VALUES (%s, %s, %s)",
            [
                user_id,
                "exercise_evaluated",
                json.dumps({"exercise_id": exercise_id, "lesson_id": exercise["lesson_id"], "dont_know": False}),
            ],
        )

    # ═══════════════════════════════════════════
    # 10. Формируем ответ
    # ═══════════════════════════════════════════
    words_response = []
    for tw in updated_target_words:
        wd = words_data.get(tw["word_id"])
        words_response.append(
            {
                "word_id": tw["word_id"],
                "lemma": wd["lemma"] if wd else "",
                "pos": wd["pos"] if wd else "",
                "surface_form": tw["surface_form"],
                "result": tw["result"],
                "user_fragment": tw["user_fragment"],
                "translations": wd["translations"] if wd else [],
            }
        )

    return {
        "exercise_id": exercise_id,
        "target_sentence": exercise["target_sentence"],
        "reference_translation": exercise["reference_translation"],
        "user_translation": user_translation,
        "words": words_response,
        "suggestions": all_suggestions,
        "lesson_completed": lesson_completed,
    }


async def _process_suggestions(
    db: AsyncConnection, profile_id: int, target_word_ids: list[int], suggested_raw: list[dict]
) -> list[dict]:
    if not suggested_raw:
        return []
    seen = set()
    normalized = []
    for s in suggested_raw:
        lemma = s.get("lemma", "").strip().lower()
        pos = s.get("pos", "")
        if not lemma or not pos:
            continue
        lemma_key = compute_lemma_key(lemma)
        key = (lemma_key, pos)
        if key in seen:
            continue
        seen.add(key)
        normalized.append({"lemma": lemma, "lemma_key": lemma_key, "pos": pos})

    target_keys = set()
    if target_word_ids:
        cur = await db.execute("SELECT lemma_key, pos FROM words WHERE id = ANY(%s)", [target_word_ids])
        target_keys = {(r["lemma_key"], r["pos"]) for r in await cur.fetchall()}
    normalized = [s for s in normalized if (s["lemma_key"], s["pos"]) not in target_keys]

    suggestions = []
    for s in normalized:
        cur = await db.execute(
            "SELECT id, lemma, pos, translations FROM words WHERE lemma_key = %s AND pos = %s",
            [s["lemma_key"], s["pos"]],
        )
        word = await cur.fetchone()
        if not word:
            continue
        cur = await db.execute(
            "SELECT id FROM user_words WHERE learning_profile_id = %s AND word_id = %s",
            [profile_id, word["id"]],
        )
        if await cur.fetchone():
            continue
        suggestions.append(
            {
                "word_id": word["id"],
                "lemma": word["lemma"],
                "pos": word["pos"],
                "translations": word["translations"],
                "state": "suggested",
                "suggestion_type": "new",
            }
        )
        if len(suggestions) >= MAX_REGULAR_SUGGESTIONS:
            break
    return suggestions


async def _process_error_suggestions(
    db: AsyncConnection, profile_id: int, nontarget_words: list[dict], errors_raw: list[dict], user_translation: str
) -> list[dict]:
    if not errors_raw or not nontarget_words:
        return []
    nontarget_index = {nt["word_id"]: nt for nt in nontarget_words}
    seen_word_ids = set()
    suggestions = []

    for err in errors_raw:
        if not isinstance(err, dict):
            continue
        word_id = err.get("word_id")
        user_fragment = err.get("user_fragment")
        correct_translation = err.get("correct_translation")

        if word_id not in nontarget_index:
            continue
        if word_id in seen_word_ids:
            continue
        seen_word_ids.add(word_id)

        nt_word = nontarget_index[word_id]
        word_translations = nt_word.get("translations", [])

        if user_fragment:
            normalized_fragment = normalize_for_comparison(user_fragment)
            if any(normalized_fragment == normalize_for_comparison(t) for t in word_translations):
                continue
            if correct_translation and normalized_fragment == normalize_for_comparison(correct_translation):
                continue
            
            validated_fragment = validate_user_fragment(user_translation, user_fragment)
            if validated_fragment is None:
                continue
            user_fragment = validated_fragment
        else:
            continue

        cur = await db.execute(
            "SELECT id FROM user_words WHERE learning_profile_id = %s AND word_id = %s",
            [profile_id, word_id],
        )
        if await cur.fetchone():
            continue

        suggestions.append(
            {
                "word_id": word_id,
                "lemma": nt_word["lemma"],
                "pos": nt_word["pos"],
                "translations": nt_word.get("translations", []),
                "state": "suggested",
                "suggestion_type": "error",
                "user_fragment": user_fragment,
                "correct_translation": correct_translation,
            }
        )
        if len(suggestions) >= MAX_ERROR_SUGGESTIONS:
            break
    return suggestions


async def _build_saved_result(db: AsyncConnection, exercise_id: int) -> dict:
    """
    Строит ответ для уже оценённого упражнения (идемпотентность).
    """
    # ИСПРАВЛЕНИЕ: Добавлен JOIN с lessons для получения актуального статуса урока
    cur = await db.execute(
        """SELECT le.id, le.target_sentence, le.reference_translation, le.user_translation,
            le.target_words, le.suggested_words, le.dont_know, l.status as lesson_status
        FROM lesson_exercises le
        JOIN lessons l ON l.id = le.lesson_id
        WHERE le.id = %s""",
        [exercise_id],
    )
    exercise = await cur.fetchone()
    if not exercise:
        raise ValueError("exercise_not_found")

    # ИСПРАВЛЕНИЕ: Корректно определяем, завершен ли урок
    lesson_completed = exercise["lesson_status"] == "completed"

    target_words = exercise["target_words"]
    suggested_words = exercise["suggested_words"]

    word_ids = [tw["word_id"] for tw in target_words]
    cur = await db.execute(
        "SELECT id, lemma, pos, translations FROM words WHERE id = ANY(%s)", [word_ids]
    )
    words_data = {r["id"]: r for r in await cur.fetchall()}

    words_response = []
    for tw in target_words:
        wd = words_data.get(tw["word_id"])
        words_response.append(
            {
                "word_id": tw["word_id"],
                "lemma": wd["lemma"] if wd else "",
                "pos": wd["pos"] if wd else "",
                "surface_form": tw["surface_form"],
                "result": tw["result"],
                "user_fragment": tw["user_fragment"],
                "translations": wd["translations"] if wd else [],
            }
        )

    suggestions = []
    for sw in suggested_words:
        cur = await db.execute(
            "SELECT id, lemma, pos, translations FROM words WHERE id = %s", [sw["word_id"]]
        )
        word = await cur.fetchone()
        if word:
            suggestion = {
                "word_id": word["id"],
                "lemma": word["lemma"],
                "pos": word["pos"],
                "translations": word["translations"],
                "state": sw["state"],
                "suggestion_type": sw.get("suggestion_type", "new"),
            }
            if sw.get("suggestion_type") == "error":
                suggestion["user_fragment"] = sw.get("user_fragment")
                suggestion["correct_translation"] = sw.get("correct_translation")
            suggestions.append(suggestion)

    return {
        "exercise_id": exercise_id,
        "target_sentence": exercise["target_sentence"],
        "reference_translation": exercise["reference_translation"],
        "user_translation": exercise["user_translation"],
        "words": words_response,
        "suggestions": suggestions,
        "lesson_completed": lesson_completed,
    }