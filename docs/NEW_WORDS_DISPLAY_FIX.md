# 🐛 Исправление проблемы с отображением новых слов на странице упражнения

## Дата
2026-01-15

## Проблема

Новые слова, добавленные перед генерацией урока, не отображались на странице упражнения, в котором они должны были быть.

### Симптомы

- На странице preview новые слова отображались корректно
- После нажатия "Начать урок" и генерации предложений LLM
- На странице упражнения целевые слова не отображались или отображались с пустым `surface_form`

## Причина

Проблема была в процессе сопоставления слов между входными данными и ответом LLM:

### 1. LLM генерировал собственные `word_id`

LLM возвращал ответ в формате:
```json
{
  "words": [
    {"word_id": 1, "lemma": "bright", "pos": "adj", "surface_form": "Bright"},
    {"word_id": 2, "lemma": "bite", "pos": "verb", "surface_form": "bites"}
  ]
}
```

Но реальные `word_id` из базы данных были другими (например, 123, 456).

### 2. Сопоставление только по `lemma` и `pos`

Код в `lesson_start.py` пытался сопоставить слова только по `lemma` и `pos`:
```python
for w in result["words"]:
    if (
        w["lemma"].lower() == word_data[wid]["lemma"].lower()
        and w["pos"] == word_data[wid]["pos"]
    ):
        sf = w["surface_form"]
        ...
```

Если LLM возвращал `lemma` в другой форме (например, "running" вместо "run"), сопоставление не происходило, и `surface_form` оставался `None`.

### 3. Отсутствие fallback

Если сопоставление не удавалось, слово добавлялось в `target_words_json` с `surface_form: None`, что приводило к тому, что слово не отображалось на странице упражнения.

## Решение

### 1. Передаём `word_id` в LLM

Обновлён код в `lesson_start.py` для передачи `word_id` в LLM:

```python
# Подготавливаем данные для LLM
word_data = {}
for w in preview.get("due_words", []):
    word_data[w["word_id"]] = {"word_id": w["word_id"], "lemma": w["lemma"], "pos": w["pos"]}
for w in preview.get("new_words", []):
    word_data[w["word_id"]] = {"word_id": w["word_id"], "lemma": w["lemma"], "pos": w["pos"]}
```

### 2. Обновлён промпт для LLM

Добавлена явная инструкция о том, что LLM должен возвращать `word_id` из входных данных:

```
10. ВАЖНО: Верни word_id ТОЧНО ТАКИМ ЖЕ, как во входных данных. Не генерируй новые word_id (1, 2, 3...), а используй те, что были переданы во входном JSON.
```

И обновлён пример:
```json
{
  "words": [
    {
      "word_id": 123,
      "lemma": "bright",
      "pos": "adj",
      "surface_form": "Bright"
    }
  ]
}
```

Вместо:
```json
{
  "words": [
    {
      "word_id": 1,
      "lemma": "bright",
      "pos": "adj",
      "surface_form": "Bright"
    }
  ]
}
```

### 3. Улучшено сопоставление в `lesson_start.py`

Теперь код сначала пытается сопоставить по `word_id`, а если не получается - по `lemma` и `pos`:

```python
for w in result["words"]:
    # Сначала пробуем сопоставить по word_id
    if w.get("word_id") == wid:
        sf = w["surface_form"]
        lemma = w["lemma"]
        pos = w["pos"]
        print(f"   ✅ Найдено совпадение по word_id! surface_form={sf}")
        break
    # Если word_id не совпадает, пробуем по lemma и pos
    elif (
        w["lemma"].lower() == word_data[wid]["lemma"].lower()
        and w["pos"] == word_data[wid]["pos"]
    ):
        sf = w["surface_form"]
        lemma = w["lemma"]
        pos = w["pos"]
        print(f"   ✅ Найдено совпадение по lemma/pos! surface_form={sf}")
        break
else:
    print(f"   ❌ Совпадение НЕ найдено! Используем fallback")
    # Fallback: используем lemma из word_data как surface_form
    sf = word_data[wid]["lemma"]
    lemma = word_data[wid]["lemma"]
    pos = word_data[wid]["pos"]
    print(f"   ⚠️ Fallback: surface_form={sf}")
```

### 4. Добавлено подробное логирование

Добавлено логирование для отладки процесса сопоставления:

```python
print(f"\n{'='*80}")
print(f"📝 Формирование target_words для группы {idx}")
print(f"{'='*80}")
print(f"Group words (word_id): {group_words}")
print(f"LLM returned words: {result.get('words', [])}")

for wid in group_words:
    print(f"\n🔍 Обработка слова word_id={wid} (is_new={is_new})")
    print(f"   Ожидаемое lemma: {word_data[wid]['lemma']}")
    print(f"   Ожидаемое pos: {word_data[wid]['pos']}")
    
    for w in result["words"]:
        print(f"   Проверяем LLM слово: word_id={w.get('word_id')}, lemma={w.get('lemma')}, pos={w.get('pos')}, surface_form={w.get('surface_form')}")
        ...

print(f"\n📊 Итоговые target_words:")
for tw in target_words_json:
    print(f"   word_id={tw['word_id']}, lemma={tw['lemma']}, pos={tw['pos']}, surface_form={tw['surface_form']}, is_new={tw['is_new']}")
```

## Изменённые файлы

1. **`backend/app/services/lesson_start.py`**
   - Добавлена передача `word_id` в `word_data`
   - Улучшено сопоставление слов (сначала по `word_id`, потом по `lemma`/`pos`)
   - Добавлен fallback для случая, когда совпадение не найдено
   - Добавлено подробное логирование

2. **`sql/001_init.sql`**
   - Обновлён промпт `generate_sentences` с инструкцией о `word_id`

3. **`scripts/update_prompt.py`**
   - Обновлён промпт с инструкцией о `word_id`
   - Обновлён пример с реальными `word_id` (123, 456 вместо 1, 2)

## Как применить

### 1. Обновите промпт в базе данных

```bash
cd backend
python ../scripts/update_prompt.py
```

### 2. Перезапустите бэкенд

```bash
uvicorn app.main:app --reload
```

### 3. Проверьте работу

1. Создайте новый урок
2. Добавьте новые слова через подсказки
3. Начните новый урок
4. Проверьте логи бэкенда - должно быть подробное логирование процесса сопоставления
5. Проверьте страницу упражнения - все целевые слова должны отображаться

## Ожидаемое поведение

### До исправления

- Новые слова не отображались на странице упражнения
- `surface_form` был `None` или пустой
- В логах не было информации о процессе сопоставления

### После исправления

- Все слова (и due, и new) отображаются на странице упражнения
- `surface_form` всегда заполнен (либо из ответа LLM, либо через fallback)
- В логах виден подробный процесс сопоставления:
  ```
  🔍 Обработка слова word_id=123 (is_new=True)
     Ожидаемое lemma: bright
     Ожидаемое pos: adj
     Проверяем LLM слово: word_id=123, lemma=bright, pos=adj, surface_form=Bright
     ✅ Найдено совпадение по word_id! surface_form=Bright
  ```

## Fallback механизм

Если LLM не вернул `word_id` или вернул неправильный `word_id`, код использует fallback:

1. Сначала пытается сопоставить по `word_id` (предпочтительный способ)
2. Если не получилось - пытается сопоставить по `lemma` и `pos`
3. Если и это не получилось - использует `lemma` из `word_data` как `surface_form`

Это гарантирует, что слово всегда будет отображаться на странице упражнения, даже если LLM не вернул корректные данные.

## Тестирование

### Тест 1: Новые слова из подсказок

1. Завершите урок с подсказками
2. Добавьте несколько слов через подсказки
3. Начните новый урок
4. Проверьте, что добавленные слова отображаются на странице упражнения

### Тест 2: Due слова

1. Завершите урок
2. Начните новый урок (должны появиться due слова)
3. Проверьте, что due слова отображаются на странице упражнения

### Тест 3: Смешанные слова

1. Добавьте новые слова через подсказки
2. Начните новый урок (должны быть и due, и new слова)
3. Проверьте, что все слова отображаются на странице упражнения

### Проверка логов

В логах бэкенда должно быть:
```
📝 Формирование target_words для группы 0
================================================================================
Group words (word_id): [123, 456]
LLM returned words: [{'word_id': 123, 'lemma': 'bright', ...}, ...]

🔍 Обработка слова word_id=123 (is_new=True)
   Ожидаемое lemma: bright
   Ожидаемое pos: adj
   Проверяем LLM слово: word_id=123, lemma=bright, pos=adj, surface_form=Bright
   ✅ Найдено совпадение по word_id! surface_form=Bright

🔍 Обработка слова word_id=456 (is_new=False)
   Ожидаемое lemma: bite
   Ожидаемое pos: verb
   Проверяем LLM слово: word_id=456, lemma=bite, pos=verb, surface_form=bites
   ✅ Найдено совпадение по word_id! surface_form=bites

📊 Итоговые target_words:
   word_id=123, lemma=bright, pos=adj, surface_form=Bright, is_new=True
   word_id=456, lemma=bite, pos=verb, surface_form=bites, is_new=False
```

## Статус

✅ Обновлён код передачи `word_id` в LLM  
✅ Обновлён промпт с инструкцией о `word_id`  
✅ Улучшено сопоставление слов (по `word_id` и по `lemma`/`pos`)  
✅ Добавлен fallback для случая, когда совпадение не найдено  
✅ Добавлено подробное логирование  
✅ Проект успешно собирается  
✅ Готово к тестированию

---

**Версия:** 1.22.0  
**Дата:** 2026-01-15
