# 🔧 Исправление формата ответа LLM

## Проблема

LLM возвращает ответ в неправильном формате:

**Что возвращает LLM:**
```json
{
  "sentences": [
    {
      "sentence": "The bright carpet makes the room look warm.",
      "reference_translation": "Яркий ковер делает комнату уютной.",
      "surface_forms": {"bright": "bright", "carpet": "carpet"}
    }
  ]
}
```

**Что ожидает код:**
```json
[
  {
    "group_index": 0,
    "sentence": "The bright carpet makes the room look warm.",
    "reference_translation": "Яркий ковер делает комнату уютной.",
    "words": [
      {
        "word_id": 1,
        "lemma": "bright",
        "pos": "adj",
        "surface_form": "bright"
      }
    ]
  }
]
```

## Различия

| Проблема | LLM возвращает | Код ожидает |
|----------|----------------|-------------|
| Структура | Объект `{"sentences": [...]}` | Массив `[...]` |
| Идентификатор группы | Отсутствует | `group_index: 0` |
| Поле слов | `surface_forms: {...}` | `words: [...]` |
| Формат слов | Словарь `{lemma: surface_form}` | Массив объектов с `word_id`, `lemma`, `pos`, `surface_form` |

## Решение

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
cd backend
uvicorn app.main:app --reload
```

### Шаг 3: Проверьте логи

Запустите урок через фронтенд и проверьте логи. Теперь должно быть:

```
📥 LLM RAW RESPONSE
Content (full):
[
  {
    "group_index": 0,
    "sentence": "She runs every morning.",
    "reference_translation": "Она бегает каждое утро.",
    "words": [
      {
        "word_id": 1,
        "lemma": "run",
        "pos": "verb",
        "surface_form": "runs"
      }
    ]
  }
]
```

## Что изменилось в промпте

Добавлены явные инструкции:

1. **"Верни СТРОГО JSON-МАССИВ (не объект!)"** - запрещает возвращать объект с полем "sentences"
2. **"Каждый элемент массива должен содержать поле 'group_index'"** - требует идентификатор группы
3. **"Поле 'words' должно быть массивом объектов"** - требует правильный формат поля слов
4. **"НЕ возвращай объект с полем 'sentences'. Возвращай МАССИВ напрямую."** - явный запрет
5. **"НЕ используй поле 'surface_forms'. Используй поле 'words' с массивом объектов."** - явный запрет

Добавлен подробный пример правильного формата ответа.

## Проверка

### Проверьте промпт в БД

```sql
SELECT key, system_template FROM prompts WHERE key = 'generate_sentences';
```

Должен содержать:
- "Верни СТРОГО JSON-МАССИВ"
- "group_index"
- "words"
- Пример с массивом `[...]`

### Проверьте логи

После запуска урока в логах должно быть:

```
✅ generate_sentences() COMPLETED
Response type: <class 'list'>
Response: [
  {
    "group_index": 0,
    "sentence": "...",
    "reference_translation": "...",
    "words": [...]
  }
]
```

НЕ должно быть:
```
Response: {'sentences': [...]}
```

## Если проблема сохраняется

### Вариант 1: Уменьшите температуру

В `backend/.env`:
```env
GEN_TEMPERATURE=0.3
```

Перезапустите бэкенд.

### Вариант 2: Попробуйте другую модель

В `backend/.env`:
```env
GIGACHAT_MODEL=GigaChat-2-Max
```

Перезапустите бэкенд.

### Вариант 3: Добавьте маппинг полей (временное решение)

Если LLM продолжает возвращать неправильный формат, можно добавить маппинг в `helpers.py`:

```python
# После получения result от LLM
if isinstance(result, dict) and "sentences" in result:
    # Преобразуем формат
    sentences = result["sentences"]
    result = []
    for idx, sentence in enumerate(sentences):
        # Преобразуем surface_forms в words
        words = []
        if "surface_forms" in sentence:
            for lemma, surface_form in sentence["surface_forms"].items():
                words.append({
                    "lemma": lemma,
                    "surface_form": surface_form,
                    # word_id и pos нужно будет получить из БД
                })
        
        result.append({
            "group_index": idx,
            "sentence": sentence["sentence"],
            "reference_translation": sentence["reference_translation"],
            "words": words
        })
```

Но лучше исправить промпт, чтобы LLM сразу возвращал правильный формат.

## Статус

✅ Обновлён промпт в БД  
✅ Создан скрипт `scripts/update_prompt.py`  
✅ Обновлён SQL скрипт `sql/check_prompts.sql`  
✅ Создана документация

---

**Версия:** 1.10.0  
**Дата:** 2026-01-15
