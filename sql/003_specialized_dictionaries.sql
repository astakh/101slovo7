-- =====================================================================
-- 101slovo MVP | Migration 003: Specialized Dictionaries
-- =====================================================================

INSERT INTO dictionaries (code, name, description)
VALUES
  ('it', 'IT и технологии', 'Терминология для IT-специалистов: программирование, сети, базы данных, DevOps'),
  ('travel', 'Путешествия', 'Слова и фразы для путешествий: транспорт, отель, еда, ориентация')
ON CONFLICT (code) DO NOTHING;

INSERT INTO schema_migrations (version) VALUES ('003_specialized_dictionaries')
ON CONFLICT (version) DO NOTHING;