"""
101slovo — Сервис старта урока.
Реализует алгоритм 5.4 из ТЗ: идемпотентность, advisory locks, сверка состава,
кластеризация, генерация предложений через LLM, валидация ответа, финальная транзакция.

Изменения (диагностика 503):
- Добавлено детальное логирование каждого этапа
- Логирование типа и содержимого исключений LLM
- Логирование advisory lock и транзакций
"""

import json
import logging
import time
import traceback

from psycopg import AsyncConnection

from app.core.exceptions import LlmInvalidResponse, LlmUnavailable
from app.services.lesson_preview import get_preview_data
from app.services.llm.helpers import generate_sentences
from app.utils.clustering import cluster_words
from app.utils.datetime import get_user_today
from app.utils.ranking import compute_seed
from app.utils.sentence_validation import validate_group_response
from app.utils.text_validation import compute_lemma_key

logger = logging.getLogger(__name__)


async def start_lesson(
    db: AsyncConnection,
    *,
    user_id: int,
    profile_id: int,
    word_ids: list[int],
    idempotency_key: str,
) -> dict:
    """
    Алгоритм 5.4: Старт урока.
    """
    logger.info(f"[start_lesson] ═══════════════════════════════════════════")
    logger.info(f"[start_lesson] 🚀 НАЧАЛО: user_id={user_id}, profile_id={profile_id}, "
                f"word_ids={word_ids}, idempotency_key={idempotency_key[:20]}...")

    # ═══════════════════════════════════════════
    # 1. Валидация идемпотентности
    # ═══════════════════════════════════════════
    logger.info(f"[start_lesson] [1/10] Проверка идемпотентности...")
    if not idempotency_key or len(idempotency_key) > 128:
        logger.error(f"[start_lesson] ❌ invalid_idempotency_key")
        raise ValueError("invalid_idempotency_key")

    cur = await db.execute(
        """SELECT id, lesson_number, status FROM lessons
        WHERE learning_profile_id = %s AND idempotency_key = %s""",
        [profile_id, idempotency_key],
    )
    existing_lesson = await cur.fetchone()
    if existing_lesson:
        logger.info(f"[start_lesson] Найден существующий урок: id={existing_lesson['id']}, "
                     f"status={existing_lesson['status']}")
        if existing_lesson["status"] == "in_progress":
            return await _build_existing_lesson_response(
                db, existing_lesson["id"], existing_lesson["lesson_number"]
            )
        elif existing_lesson["status"] == "completed":
            raise ValueError("lesson_completed")

    # ═══════════════════════════════════════════
    # 2. Предпроверки
    # ═══════════════════════════════════════════
    logger.info(f"[start_lesson] [2/10] Предпроверки (онбординг, in_progress, лимит)...")
    cur = await db.execute(
        """SELECT id FROM lessons
        WHERE learning_profile_id = %s AND status = 'in_progress'""",
        [profile_id],
    )
    if await cur.fetchone():
        logger.warning(f"[start_lesson] ⚠️ resume_available для profile_id={profile_id}")
        raise ValueError("resume_available")

    cur = await db.execute(
        """SELECT u.timezone, lp.daily_lesson_limit
        FROM users u JOIN learning_profiles lp ON lp.user_id = u.id
        WHERE lp.id = %s""",
        [profile_id],
    )
    profile_row = await cur.fetchone()
    if not profile_row:
        raise ValueError("profile_not_found")

    today = get_user_today(profile_row["timezone"])
    cur = await db.execute(
        """SELECT COUNT(*) as cnt FROM lessons
        WHERE learning_profile_id = %s AND started_local_date = %s""",
        [profile_id, today],
    )
    lessons_today = (await cur.fetchone())["cnt"]
    logger.info(f"[start_lesson] Уроков сегодня: {lessons_today}/{profile_row['daily_lesson_limit']}")

    if lessons_today >= profile_row["daily_lesson_limit"]:
        raise ValueError("limit_reached")

    # ═══════════════════════════════════════════
    # 3. Advisory lock
    # ═══════════════════════════════════════════
    logger.info(f"[start_lesson] [3/10] Захват advisory lock для profile_id={profile_id}...")
    cur = await db.execute(
        "SELECT pg_try_advisory_lock(%s) as lock_acquired", [profile_id]
    )
    result = await cur.fetchone()
    lock_acquired = result["lock_acquired"] if result else False
    logger.info(f"[start_lesson] Lock acquired: {lock_acquired}")
    if not lock_acquired:
        raise ValueError("start_in_progress")

    try:
        # ═══════════════════════════════════════════
        # 4. Сверка состава
        # ═══════════════════════════════════════════
        logger.info(f"[start_lesson] [4/10] Сверка состава с preview...")
        preview = await get_preview_data(db, profile_id)
        logger.info(f"[start_lesson] Preview state: {preview.get('state')}")
        if preview.get("state") != "ready":
            raise ValueError("preview_outdated")

        expected_word_ids = set(
            [w["word_id"] for w in preview.get("due_words", [])]
            + [w["word_id"] for w in preview.get("new_words", [])]
        )
        logger.info(f"[start_lesson] Expected word_ids: {expected_word_ids}")
        logger.info(f"[start_lesson] Received word_ids: {set(word_ids)}")

        if set(word_ids) != expected_word_ids:
            logger.warning(f"[start_lesson] ⚠️ preview_outdated: mismatch")
            raise ValueError("preview_outdated")

        # ═══════════════════════════════════════════
        # 5. Кластеризация
        # ═══════════════════════════════════════════
        logger.info(f"[start_lesson] [5/10] Кластеризация слов...")
        seed = compute_seed(profile_id, preview["lesson_number"])
        groups = cluster_words(word_ids, seed)
        logger.info(f"[start_lesson] Создано {len(groups)} групп: "
                     f"размеры {[len(g) for g in groups]}")

        word_data = {}
        for w in preview.get("due_words", []):
            word_data[w["word_id"]] = {
                "word_id": w["word_id"], "lemma": w["lemma"], "pos": w["pos"]
            }
        for w in preview.get("new_words", []):
            word_data[w["word_id"]] = {
                "word_id": w["word_id"], "lemma": w["lemma"], "pos": w["pos"]
            }

        llm_groups = []
        for idx, group in enumerate(groups):
            llm_groups.append(
                {"group_index": idx, "words": [word_data[wid] for wid in group]}
            )

        # ═══════════════════════════════════════════
        # 6-8. Генерация и валидация с повторами
        # ═══════════════════════════════════════════
        logger.info(f"[start_lesson] [6-8/10] ГЕНЕРАЦИЯ ПРЕДЛОЖЕНИЙ ЧЕРЕЗ LLM...")
        deadline = time.monotonic() + 45.0
        valid_results = {}
        pending_groups = llm_groups.copy()
        max_content_retries = 2
        attempt = 0

        while pending_groups and attempt <= max_content_retries:
            attempt += 1
            cur = await db.execute(
                "SELECT level FROM learning_profiles WHERE id = %s", [profile_id]
            )
            level = (await cur.fetchone())["level"]
            logger.info(f"[start_lesson] 📤 ATTEMPT {attempt}/{max_content_retries + 1}: "
                         f"level={level}, pending_groups={len(pending_groups)}")

            try:
                logger.info(f"[start_lesson] Вызываем generate_sentences()...")
                response = await generate_sentences(
                    db, level=level, groups=pending_groups, user_id=user_id
                )
                logger.info(f"[start_lesson] ✅ generate_sentences() вернул ответ: "
                             f"type={type(response).__name__}, "
                             f"items={len(response) if isinstance(response, list) else 'N/A'}")

                # Логируем первые 500 символов ответа для диагностики
                response_str = json.dumps(response, ensure_ascii=False)
                logger.info(f"[start_lesson] Response preview: {response_str[:500]}...")

            except LlmUnavailable as e:
                logger.error(f"[start_lesson] ❌ LlmUnavailable: {e}")
                logger.error(f"[start_lesson] Traceback:\n{traceback.format_exc()}")
                raise
            except LlmInvalidResponse as e:
                logger.error(f"[start_lesson] ❌ LlmInvalidResponse: {e}")
                logger.error(f"[start_lesson] Traceback:\n{traceback.format_exc()}")
                raise
            except Exception as e:
                logger.error(f"[start_lesson] ❌ UNEXPECTED Exception: "
                             f"type={type(e).__name__}, message={e}")
                logger.error(f"[start_lesson] Traceback:\n{traceback.format_exc()}")
                raise LlmUnavailable(f"llm_unavailable: {type(e).__name__}: {e}")

            if not isinstance(response, list):
                logger.error(f"[start_lesson] ❌ Response is not a list: {type(response)}")
                raise LlmInvalidResponse("LLM response is not a list")

            # Валидируем ответ
            all_sentences = [r.get("sentence", "") for r in valid_results.values()]
            response_by_index = {}
            for entry in response:
                if not isinstance(entry, dict):
                    logger.warning(f"[start_lesson] ⚠️ Skipping non-dict entry: {type(entry)}")
                    continue
                gi = entry.get("group_index")
                if gi is not None:
                    response_by_index[gi] = entry

            logger.info(f"[start_lesson] Response содержит {len(response_by_index)} групп: "
                         f"indices={list(response_by_index.keys())}")

            new_pending = []
            for pg in pending_groups:
                gi = pg["group_index"]
                if gi not in response_by_index:
                    logger.warning(f"[start_lesson] ⚠️ Group {gi} отсутствует в ответе LLM")
                    new_pending.append(pg)
                    continue

                entry = response_by_index[gi]
                error = validate_group_response(gi, pg["words"], entry, all_sentences)
                if error:
                    logger.warning(f"[start_lesson] ⚠️ Group {gi} validation failed: {error}")
                    new_pending.append(pg)
                else:
                    logger.info(f"[start_lesson] ✅ Group {gi} validated OK")
                    valid_results[gi] = entry
                    all_sentences.append(entry["sentence"])

            pending_groups = new_pending
            logger.info(f"[start_legend] Валидация завершена: "
                         f"valid={len(valid_results)}, pending={len(pending_groups)}")

            if time.monotonic() > deadline - 5:
                logger.warning(f"[start_lesson] ⏰ Deadline близок, прерываем retries")
                break

        if pending_groups:
            logger.error(f"[start_lesson] ❌ Остались невалидные группы: "
                          f"{[pg['group_index'] for pg in pending_groups]}")
            raise LlmInvalidResponse("llm_invalid_response")

        logger.info(f"[start_lesson] ✅ ВСЕ {len(valid_results)} групп успешно сгенерированы")

        # ═══════════════════════════════════════════
        # 9. Транзакция записи
        # ═══════════════════════════════════════════
        logger.info(f"[start_lesson] [9/10] Начало транзакции записи в БД...")
        async with db.transaction():
            cur = await db.execute(
                """SELECT id, last_lesson_number FROM learning_profiles
                WHERE id = %s FOR UPDATE""",
                [profile_id],
            )
            locked_profile = await cur.fetchone()
            if not locked_profile:
                raise ValueError("profile_not_found")

            expected_next = locked_profile["last_lesson_number"] + 1
            if expected_next != preview["lesson_number"]:
                raise ValueError("preview_outdated")

            # Повторная проверка идемпотентности
            cur = await db.execute(
                """SELECT id FROM lessons
                WHERE learning_profile_id = %s AND idempotency_key = %s""",
                [profile_id, idempotency_key],
            )
            if await cur.fetchone():
                raise ValueError("idempotency_key_taken")

            # Повторная проверка лимита
            cur = await db.execute(
                """SELECT COUNT(*) as cnt FROM lessons
                WHERE learning_profile_id = %s AND started_local_date = %s""",
                [profile_id, today],
            )
            if (await cur.fetchone())["cnt"] >= profile_row["daily_lesson_limit"]:
                raise ValueError("limit_reached")

            # Повторная проверка слов
            due_word_ids = {w["word_id"] for w in preview.get("due_words", [])}
            new_word_ids = {w["word_id"] for w in preview.get("new_words", [])}
            if due_word_ids:
                cur = await db.execute(
                    """SELECT word_id FROM user_words
                    WHERE learning_profile_id = %s AND word_id = ANY(%s)
                    AND status = 'active' AND due_lesson_number <= %s""",
                    [profile_id, list(due_word_ids), expected_next],
                )
                valid_due = {r["word_id"] for r in await cur.fetchall()}
                if valid_due != due_word_ids:
                    raise ValueError("words_changed")

            if new_word_ids:
                cur = await db.execute(
                    """SELECT word_id FROM user_words
                    WHERE learning_profile_id = %s AND word_id = ANY(%s)""",
                    [profile_id, list(new_word_ids)],
                )
                existing_new = {r["word_id"] for r in await cur.fetchall()}
                if existing_new:
                    raise ValueError("words_changed")

            # Записываем новые слова в user_words
            for wid in new_word_ids:
                await db.execute(
                    """INSERT INTO user_words
                    (learning_profile_id, word_id, status, stage, due_lesson_number, source)
                    VALUES (%s, %s, 'active', 0, %s, 'dictionary')""",
                    [profile_id, wid, expected_next],
                )

            # Обновляем профиль
            await db.execute(
                """UPDATE learning_profiles
                SET last_lesson_number = %s, updated_at = now()
                WHERE id = %s""",
                [expected_next, profile_id],
            )

            # Вставляем урок
            cur = await db.execute(
                """INSERT INTO lessons
                (learning_profile_id, lesson_number, idempotency_key, status,
                started_at, started_local_date)
                VALUES (%s, %s, %s, 'in_progress', now(), %s)
                RETURNING id""",
                [profile_id, expected_next, idempotency_key, today],
            )
            lesson_id = (await cur.fetchone())["id"]
            logger.info(f"[start_lesson] ✅ Урок создан: lesson_id={lesson_id}, "
                         f"lesson_number={expected_next}")

            # Вставляем упражнения
            first_exercise_id = None
            first_exercise_data = None
            for idx in range(len(groups)):
                result = valid_results[idx]
                group_words = groups[idx]

                target_words_json = []
                for wid in group_words:
                    is_new = wid in new_word_ids
                    sf = None
                    lemma = None
                    pos = None
                    for w in result["words"]:
                        if w.get("word_id") == wid:
                            sf = w["surface_form"]
                            lemma = w["lemma"]
                            pos = w["pos"]
                            break
                        elif (
                            w["lemma"].lower() == word_data[wid]["lemma"].lower()
                            and w["pos"] == word_data[wid]["pos"]
                        ):
                            sf = w["surface_form"]
                            lemma = w["lemma"]
                            pos = w["pos"]
                            break
                    if sf is None:
                        sf = word_data[wid]["lemma"]
                        lemma = word_data[wid]["lemma"]
                        pos = word_data[wid]["pos"]

                    target_words_json.append({
                        "word_id": wid,
                        "lemma": lemma or word_data[wid]["lemma"],
                        "pos": pos or word_data[wid]["pos"],
                        "surface_form": sf,
                        "is_new": is_new,
                        "stage_before": 0 if is_new else None,
                        "stage_after": None,
                        "result": None,
                        "user_fragment": None,
                    })

                for tw in target_words_json:
                    if not tw["is_new"]:
                        cur = await db.execute(
                            """SELECT stage FROM user_words
                            WHERE learning_profile_id = %s AND word_id = %s""",
                            [profile_id, tw["word_id"]],
                        )
                        row = await cur.fetchone()
                        tw["stage_before"] = row["stage"] if row else 0

                nontarget_words_raw = result.get("nontarget_words", [])
                nontarget_words_json = await _resolve_nontarget_words(
                    db, profile_id, nontarget_words_raw, group_words
                )

                cur = await db.execute(
                    """INSERT INTO lesson_exercises
                    (lesson_id, order_index, target_sentence, reference_translation,
                    status, target_words, suggested_words, nontarget_words)
                    VALUES (%s, %s, %s, %s, 'pending', %s, '[]', %s)
                    RETURNING id""",
                    [
                        lesson_id,
                        idx + 1,
                        result["sentence"],
                        result["reference_translation"],
                        json.dumps(target_words_json, ensure_ascii=False),
                        json.dumps(nontarget_words_json, ensure_ascii=False),
                    ],
                )
                exercise_id = (await cur.fetchone())["id"]

                if idx == 0:
                    first_exercise_id = exercise_id
                    first_exercise_data = {
                        "exercise_id": exercise_id,
                        "order_index": 1,
                        "sentence": result["sentence"],
                        "reference_translation": result["reference_translation"],
                        "target_words": target_words_json,
                    }

            # События
            await db.execute(
                "INSERT INTO events (user_id, type, payload) VALUES (%s, %s, %s)",
                [
                    user_id,
                    "lesson_started",
                    json.dumps({"lesson_id": lesson_id, "lesson_number": expected_next}),
                ],
            )
            for wid in new_word_ids:
                await db.execute(
                    "INSERT INTO events (user_id, type, payload) VALUES (%s, %s, %s)",
                    [user_id, "new_word_accepted", json.dumps({"word_id": wid})],
                )

        logger.info(f"[start_lesson] ✅ Транзакция успешно закоммичена")

        # ═══════════════════════════════════════════
        # 10. Ответ
        # ═══════════════════════════════════════════
        logger.info(f"[start_lesson] [10/10] 🎉 Формируем ответ клиенту")
        return {
            "lesson_id": lesson_id,
            "lesson_number": expected_next,
            "exercises_total": len(groups),
            "created": True,
            "current_exercise": first_exercise_data,
        }

    finally:
        logger.info(f"[start_lesson] 🔓 Освобождаем advisory lock...")
        await db.execute("SELECT pg_advisory_unlock(%s)", [profile_id])
        logger.info(f"[start_lesson] ═══════════════════════════════════════════")


async def _resolve_nontarget_words(
    db: AsyncConnection,
    profile_id: int,
    nontarget_words_raw: list[dict],
    target_word_ids: list[int],
) -> list[dict]:
    """
    Разрешает нецелевые слова против справочника.
    """
    if not nontarget_words_raw:
        return []

    target_keys = set()
    if target_word_ids:
        cur = await db.execute(
            "SELECT lemma_key, pos FROM words WHERE id = ANY(%s)",
            [target_word_ids],
        )
        target_keys = {(r["lemma_key"], r["pos"]) for r in await cur.fetchall()}

    seen_keys = set()
    resolved = []

    for nt_word in nontarget_words_raw:
        if not isinstance(nt_word, dict):
            continue
        lemma = nt_word.get("lemma", "").strip().lower()
        pos = nt_word.get("pos", "")
        surface_form = nt_word.get("surface_form", "")

        if not lemma or not pos or not surface_form:
            continue

        lemma_key = compute_lemma_key(lemma)
        key = (lemma_key, pos)

        if key in target_keys:
            continue
        if key in seen_keys:
            continue
        seen_keys.add(key)

        cur = await db.execute(
            "SELECT id, lemma, pos, translations FROM words "
            "WHERE lemma_key = %s AND pos = %s",
            [lemma_key, pos],
        )
        word = await cur.fetchone()
        if not word:
            logger.debug(
                f"nontarget word '{lemma}' ({pos}) not found in dictionary, skipping"
            )
            continue

        resolved.append({
            "word_id": word["id"],
            "lemma": word["lemma"],
            "pos": word["pos"],
            "surface_form": surface_form,
            "translations": word["translations"],
        })

    logger.info(
        f"Resolved {len(resolved)}/{len(nontarget_words_raw)} nontarget words"
    )
    return resolved


async def _build_existing_lesson_response(
    db: AsyncConnection, lesson_id: int, lesson_number: int
) -> dict:
    """Строит ответ для существующего урока (идемпотентный повтор)."""
    cur = await db.execute(
        """SELECT COUNT(*) as total,
        COUNT(*) FILTER (WHERE status = 'evaluated') as done
        FROM lesson_exercises WHERE lesson_id = %s""",
        [lesson_id],
    )
    stats = await cur.fetchone()

    cur = await db.execute(
        """SELECT id, order_index, target_sentence, reference_translation, target_words
        FROM lesson_exercises
        WHERE lesson_id = %s AND status = 'pending'
        ORDER BY order_index LIMIT 1""",
        [lesson_id],
    )
    exercise = await cur.fetchone()
    if not exercise:
        raise ValueError("lesson_completed")

    return {
        "lesson_id": lesson_id,
        "lesson_number": lesson_number,
        "exercises_total": stats["total"],
        "created": False,
        "current_exercise": {
            "exercise_id": exercise["id"],
            "order_index": exercise["order_index"],
            "sentence": exercise["target_sentence"],
            "reference_translation": exercise["reference_translation"],
            "target_words": exercise["target_words"],
        },
    }