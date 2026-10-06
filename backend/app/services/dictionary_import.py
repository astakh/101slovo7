"""
101slovo — Сервис импорта словарей.
Поддерживает dry_run для предварительной проверки.

Исправления:
- Поиск существующих слов по (lemma_key, pos) вместо (lemma, pos)
- При вставке нового слова вычисляется и сохраняется lemma_key
"""

import json
import unicodedata

from psycopg import AsyncConnection

from app.services.admin_audit import log_admin_action


def compute_lemma_key(lemma: str) -> str:
    """Вычисляет нормализованный ключ леммы: casefold(NFC(trim(lemma)))."""
    normalized = unicodedata.normalize("NFC", lemma.strip())
    return normalized.casefold()


async def import_dictionary(
    db: AsyncConnection,
    admin_id: int,
    file_content: bytes,
    dry_run: bool = False,
) -> dict:
    """
    Импортирует словарь из JSON файла.

    Формат файла:
    {
        "code": "business",
        "name": "Business English",
        "description": "Business vocabulary",
        "words": [
            {
                "lemma": "meeting",
                "pos": "noun",
                "level": "B1",
                "translations": ["встреча", "совещание"]
            }
        ]
    }

    Args:
        db: Соединение с БД
        admin_id: ID администратора
        file_content: Содержимое JSON файла
        dry_run: Если True, только проверяет без записи в БД

    Returns:
        Словарь с результатами импорта:
        - added: количество добавленных слов
        - updated: количество обновленных слов
        - skipped: количество пропущенных слов
        - errors: список ошибок
        - dry_run: флаг режима dry_run
    """
    # Парсинг JSON
    try:
        data = json.loads(file_content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"invalid_json: {str(e)}")

    # Валидация структуры
    if not isinstance(data, dict):
        raise ValueError("invalid_json: root must be object")

    code = data.get("code")
    name = data.get("name")
    description = data.get("description", "")
    words = data.get("words", [])

    if not code or not isinstance(code, str):
        raise ValueError("invalid_json: missing or invalid 'code'")
    if not name or not isinstance(name, str):
        raise ValueError("invalid_json: missing or invalid 'name'")
    if not isinstance(words, list):
        raise ValueError("invalid_json: 'words' must be array")

    # Валидация слов
    errors = []
    valid_words = []

    for idx, word in enumerate(words):
        if not isinstance(word, dict):
            errors.append({"index": idx, "error": "word must be object"})
            continue

        lemma = word.get("lemma")
        pos = word.get("pos")
        level = word.get("level")
        translations = word.get("translations", [])

        # Валидация полей
        if not lemma or not isinstance(lemma, str):
            errors.append({"index": idx, "lemma": lemma, "error": "missing or invalid 'lemma'"})
            continue

        if not pos or not isinstance(pos, str):
            errors.append({"index": idx, "lemma": lemma, "error": "missing or invalid 'pos'"})
            continue

        if pos not in ["noun", "verb", "adj", "adv", "pron", "prep", "conj", "num", "det", "intj"]:
            errors.append({"index": idx, "lemma": lemma, "error": f"invalid pos: {pos}"})
            continue

        if level and level not in ["A1", "A2", "B1", "B2", "C1", "C2"]:
            errors.append({"index": idx, "lemma": lemma, "error": f"invalid level: {level}"})
            continue

        if not isinstance(translations, list) or len(translations) == 0:
            errors.append({"index": idx, "lemma": lemma, "error": "translations must be non-empty array"})
            continue

        if len(translations) > 5:
            errors.append({"index": idx, "lemma": lemma, "error": "translations array too long (max 5)"})
            continue

        for t in translations:
            if not isinstance(t, str):
                errors.append({"index": idx, "lemma": lemma, "error": "translation must be string"})
                break
        else:
            valid_words.append({
                "lemma": lemma.strip(),
                "pos": pos,
                "level": level,
                "translations": translations,
            })

    # Dry run режим
    if dry_run:
        return {
            "dictionary": {"code": code, "name": name, "description": description},
            "added": 0,
            "updated": 0,
            "skipped": 0,
            "errors": errors,
            "dry_run": True,
        }

    # Реальный импорт
    added = 0
    updated = 0
    skipped = 0

    # Получаем или создаем словарь
    cur = await db.execute(
        "SELECT id FROM dictionaries WHERE code = %s",
        [code],
    )
    row = await cur.fetchone()

    if row:
        dictionary_id = row["id"]
        # Обновляем название и описание
        await db.execute(
            "UPDATE dictionaries SET name = %s, description = %s WHERE id = %s",
            [name, description, dictionary_id],
        )
    else:
        cur = await db.execute(
            """INSERT INTO dictionaries (code, name, description)
            VALUES (%s, %s, %s)
            RETURNING id""",
            [code, name, description],
        )
        dictionary_id = (await cur.fetchone())["id"]

    # Импортируем слова
    for word in valid_words:
        lemma = word["lemma"]
        pos = word["pos"]
        level = word["level"]
        translations = word["translations"]

        # ✅ ИСПРАВЛЕНО: вычисляем lemma_key для поиска
        lemma_key = compute_lemma_key(lemma)

        # ✅ ИСПРАВЛЕНО: ищем по (lemma_key, pos) вместо (lemma, pos)
        cur = await db.execute(
            "SELECT id, translations, dictionary_ids FROM words WHERE lemma_key = %s AND pos = %s",
            [lemma_key, pos],
        )
        existing = await cur.fetchone()

        if existing:
            word_id = existing["id"]
            existing_translations = existing["translations"]
            existing_dict_ids = existing["dictionary_ids"] or []

            # Объединяем переводы
            new_translations = list(set(existing_translations + translations))
            if len(new_translations) > 5:
                new_translations = new_translations[:5]

            # Добавляем dictionary_id если его нет
            if dictionary_id not in existing_dict_ids:
                new_dict_ids = existing_dict_ids + [dictionary_id]
            else:
                new_dict_ids = existing_dict_ids

            # Обновляем только если есть изменения
            if new_translations != existing_translations or new_dict_ids != existing_dict_ids:
                await db.execute(
                    """UPDATE words
                    SET translations = %s, dictionary_ids = %s, updated_at = now()
                    WHERE id = %s""",
                    [new_translations, new_dict_ids, word_id],
                )
                updated += 1
            else:
                skipped += 1
        else:
            # ✅ ИСПРАВЛЕНО: добавлен lemma_key в INSERT
            cur = await db.execute(
                """INSERT INTO words (lemma, lemma_key, pos, level, translations, dictionary_ids)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id""",
                [lemma, lemma_key, pos, level, translations, [dictionary_id]],
            )
            added += 1

    # Логируем действие
    await log_admin_action(
        db,
        admin_id=admin_id,
        action="dictionary_import",
        target_type="dictionary",
        target_id=code,
        details={
            "name": name,
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "errors_count": len(errors),
        },
    )

    return {
        "dictionary": {"id": dictionary_id, "code": code, "name": name, "description": description},
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "dry_run": False,
    }