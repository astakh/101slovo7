# 🔧 Исправление формата ответа LLM

## Проблема

LLM возвращает ответ в неправильном формате:

### Что возвращает LLM (неправильно):
```json
{
  "sentences": [
    {
      "surface_forms": ["Bright", "bites"],
      "reference_translation": "Яркий свет режет глаза.",
      "group_index": 0
    }
  ]
}
```

### Что ожидает код (правильно):
```json
[
  {
    "group_index": 0,
    "sentence": "Bright light bites the eyes.",
    "reference_translation": "Яркий свет режет глаза.",
    "words": [
      {
        "word_id": 1,
        "lemma": "bright",
        "pos": "adj",
        "surface_form": "Bright"
      },
      {
        "word_id": 2,
        "lemma": "bite",
        "pos": "verb",
        "surface_form": "bites"
      }
    ]
  }
]
```

## Критические различия

| Проблема | LLM возвращает | Код ожидает |
|----------|----------------|-------------|
| Структура | Объект `{"sentences": [...]}` | Массив `[...]` |
| Предложение | ❌ Отсутствует поле `sentence` | ✅ `sentence: "Bright light bites the eyes."` |
| Поле слов | `surface_forms: ["Bright", "bites"]` | `words: [{word_id, lemma, pos, surface_form}]` |
| Данные слов | Только surface forms | Полные данные: word_id, lemma, pos, surface_form |

## Решение

### 1. Обновлён промпт в БД

Добавлены явные инструкции:
- **"sentence" (ПОЛНОЕ предложение на английском языке!)** - обязательное поле
- **"КРИТИЧЕСКИ ВАЖНО: Поле "sentence" ОБЯЗАТЕЛЬНО должно содержать ПОЛНОЕ предложение"**
- Пример с полным предложением: `"sentence": "Bright light bites the eyes."`

### 2. Добавлен маппинг в `helpers.py`

Автоматическое преобразование формата ответа LLM:

```python
# Если sentence отсутствует, но есть surface_forms
if not sentence and "surface_forms" in sentence_data:
    surface_forms = sentence_data["surface_forms"]
    if isinstance(surface_forms, list) and surface_forms:
        # Соединяем surface_forms в предложение
        sentence = " ".join(surface_forms)

# Если words отсутствует, но есть surface_forms
if not words and "surface_forms" in sentence_data:
    surface_forms = sentence_data["surface_forms"]
    if isinstance(surface_forms, list):
        # Находим соответствующую группу в pending_groups
        pending_group = next((g for g in groups if g.get("group_index") == group_index), None)
        
        if pending_group and "words" in pending_group:
            # Преобразуем surface_forms в words
            words = []
            for i, surface_form in enumerate(surface_forms):
                if i < len(pending_group["words"]):
                    word_data = pending_group["words"][i]
                    words.append({
                        "word_id": word_data.get("word_id"),
                        "lemma": word_data.get("lemma", ""),
                        "pos": word_data.get("pos", ""),
                        "surface_form": surface_form
                    })
```

### 3. Обновлены скрипты

- `sql/check_prompts.sql` - обновлённый промпт
- `scripts/update_prompt.py` - скрипт для обновления промпта

## Как применить исправление

### Шаг 1: Обновите промпт в БД

```bash
cd backend
python ../scripts/update_prompt.py
```

Или выполните SQL вручную:

```bash
psql $DATABASE_URL -f ../sql/check_prompts.sql
```

### Шаг 2: Перезапустите бэкенд

```bash
uvicorn app.main:app --reload
```

### Шаг 3: Проверьте логи

Запустите урок через фронтенд и проверьте логи. Теперь должно быть:

```
🔄 NORMALIZING LLM RESPONSE
================================================================================
✅ Converted surface_forms to words for group 0
📝 Normalized entry 0:
   sentence: 'Bright light bites the eyes.'
   reference_translation: 'Яркий свет режет глаза.'
   words count: 2
```

## Ожидаемый результат

После применения исправления:

1. **LLM возвращает** (в идеале):
```json
[
  {
    "group_index": 0,
    "sentence": "Bright light bites the eyes.",
    "reference_translation": "Яркий свет режет глаза.",
    "words": [
      {
        "word_id": 1,
        "lemma": "bright",
        "pos": "adj",
        "surface_form": "Bright"
      }
    ]
  }
]
```

2. **Если LLM всё ещё возвращает старый формат**, маппинг автоматически преобразует:
```json
{
  "sentences": [
    {
      "surface_forms": ["Bright", "bites"],
      "reference_translation": "Яркий свет режет глаза.",
      "group_index": 0
    }
  ]
}
```

В:
```json
[
  {
    "group_index": 0,
    "sentence": "Bright bites",  // Сгенерировано из surface_forms
    "reference_translation": "Яркий свет режет глаза.",
    "words": [
      {
        "word_id": 1,
        "lemma": "bright",
        "pos": "adj",
        "surface_form": "Bright"
      },
      {
        "word_id": 2,
        "lemma": "bite",
        "pos": "verb",
        "surface_form": "bites"
      }
    ]
  }
]
```

## Проверка

### Проверьте промпт в БД

```sql
SELECT key, system_template FROM prompts WHERE key = 'generate_sentences';
```

Должен содержать:
- `"sentence" (ПОЛНОЕ предложение на английском языке!)`
- `"КРИТИЧЕСКИ ВАЖНО: Поле "sentence" ОБЯЗАТЕЛЬНО"`
- Пример с полным предложением

### Проверьте логи

После запуска урока в логах должно быть:

```
🔄 NORMALIZING LLM RESPONSE
✅ Converted surface_forms to words for group 0
📝 Normalized entry 0:
   sentence: 'Bright light bites the eyes.'
   reference_translation: 'Яркий свет режет глаза.'
   words count: 2
```

### Проверьте валидацию

Не должно быть ошибок:
```
❌ Validation failed: sentence empty or too long
```

## Статус

✅ Обновлён промпт в БД  
✅ Добавлен маппинг в `helpers.py`  
✅ Обновлён SQL скрипт  
✅ Обновлён Python скрипт  
✅ Создана документация  
✅ Проект успешно собирается

---

**Версия:** 1.11.0  
**Дата:** 2026-01-15
