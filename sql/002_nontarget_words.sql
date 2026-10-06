-- =====================================================================
-- 101slovo MVP | Migration 002: nontarget_words
-- =====================================================================
-- Добавляет колонку nontarget_words в lesson_exercises для хранения
-- нецелевых содержательных слов предложения, подготовленных LLM
-- на этапе генерации. Используется для детекции ошибок перевода
-- в нецелевых словах.

ALTER TABLE lesson_exercises
ADD COLUMN IF NOT EXISTS nontarget_words JSONB NOT NULL DEFAULT '[]';

ALTER TABLE lesson_exercises
ADD CONSTRAINT chk_nontarget_words_array
CHECK (jsonb_typeof(nontarget_words) = 'array');

-- Фиксация применения миграции
INSERT INTO schema_migrations (version) VALUES ('002_nontarget_words')
ON CONFLICT (version) DO NOTHING;