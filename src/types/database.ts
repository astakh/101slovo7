/**
 * 101slovo — Типы данных, соответствующие схеме БД.
 *
 * Изменения:
 * - Добавлен NontargetWord для nontarget_words
 * - Добавлен suggestion_type в SuggestedWord
 * - Добавлены user_fragment, correct_translation для ошибок перевода
 * - Убран dont_know из EvaluateRequest (кнопка «Не знаю» удалена)
 * - Добавлены типы для API-ответов (PreviewData, EvaluateResult и др.)
 */

// ========================
// Enums / Literal Types
// ========================
export type Pos =
  | 'noun'
  | 'verb'
  | 'adj'
  | 'adv'
  | 'pron'
  | 'prep'
  | 'conj'
  | 'num'
  | 'det'
  | 'intj';

export type Level = 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2';
export type ProfileLevel = 'A1' | 'A2' | 'B1' | 'B2';
export type UserWordStatus = 'active' | 'mastered' | 'ignored';
export type UserWordSource = 'dictionary' | 'suggestion' | 'decline';
export type LessonStatus = 'in_progress' | 'completed';
export type ExerciseStatus = 'pending' | 'evaluated';
export type ReportReason =
  | 'bad_sentence'
  | 'wrong_translation'
  | 'grammar_error'
  | 'other';
export type ReportStatus = 'new' | 'processed';
export type PromptKey = 'generate_sentences' | 'evaluate_translation';
export type LlmPurpose = 'generate' | 'evaluate';
export type LlmCallStatus =
  | 'ok'
  | 'http_error'
  | 'timeout'
  | 'invalid_json'
  | 'invalid_schema'
  | 'validation_failed';

// НОВОЕ: Тип подсказки
export type SuggestionType = 'new' | 'error';

// ========================
// Tables
// ========================
export interface User {
  id: number;
  email: string;
  timezone: string | null;
  timezone_changed_at: string | null;
  is_onboarded: boolean;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

export interface Dictionary {
  id: number;
  code: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface Word {
  id: number;
  lemma: string;
  lemma_key: string;
  pos: Pos;
  level: Level | null;
  translations: string[];
  dictionary_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface LearningProfile {
  id: number;
  user_id: number;
  level: ProfileLevel;
  dictionary_id: number;
  daily_lesson_limit: number;
  words_per_lesson: number;
  last_lesson_number: number;
  created_at: string;
  updated_at: string;
}

export interface UserWord {
  id: number;
  learning_profile_id: number;
  word_id: number;
  status: UserWordStatus;
  stage: number; // 0-6
  due_lesson_number: number | null;
  last_reviewed_at: string | null;
  source: UserWordSource;
  created_at: string;
  updated_at: string;
}

export interface Lesson {
  id: number;
  learning_profile_id: number;
  lesson_number: number;
  idempotency_key: string;
  status: LessonStatus;
  started_at: string;
  started_local_date: string;
  completed_at: string | null;
  completed_local_date: string | null;
}

export interface TargetWord {
  word_id: number;
  lemma: string;
  pos: Pos;
  surface_form: string;
  correct_translations: string[];
  // Поля, добавляемые после оценки:
  result?: 'correct' | 'typo' | 'incorrect';
  user_fragment?: string | null;
  stage_after?: number | null;
  stage_before?: number | null;
  is_new?: boolean;
  translations?: string[];
}

// НОВОЕ: Нецелевое слово (подготовлено на этапе генерации)
export interface NontargetWord {
  word_id: number;
  lemma: string;
  pos: Pos;
  surface_form: string;
  translations: string[];
}

// ОБНОВЛЕНО: Подсказка с типом и полями ошибки
export interface SuggestedWord {
  word_id: number;
  lemma: string;
  pos: Pos;
  translations: string[];
  state: 'suggested' | 'added' | 'ignored';
  // НОВОЕ: тип подсказки — обычная или из ошибки перевода
  suggestion_type?: SuggestionType;
  // НОВОЕ: поля для ошибок перевода (только для suggestion_type === 'error')
  user_fragment?: string | null;
  correct_translation?: string | null;
}

export interface LessonExercise {
  id: number;
  lesson_id: number;
  order_index: number;
  target_sentence: string;
  reference_translation: string;
  user_translation: string | null;
  // dont_know оставлен в БД для обратной совместимости, но больше не используется
  dont_know: boolean;
  status: ExerciseStatus;
  evaluated_at: string | null;
  target_words: TargetWord[];
  suggested_words: SuggestedWord[];
  // НОВОЕ: нецелевые слова предложения
  nontarget_words: NontargetWord[];
}

export interface SentenceReport {
  id: number;
  user_id: number;
  exercise_id: number;
  reason: ReportReason;
  comment: string | null;
  status: ReportStatus;
  admin_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface Prompt {
  key: PromptKey;
  system_template: string;
  updated_at: string;
  updated_by: number | null;
}

export interface LlmCall {
  id: number;
  created_at: string;
  purpose: LlmPurpose;
  user_id: number | null;
  lesson_id: number | null;
  exercise_id: number | null;
  attempt: number;
  request: Record<string, unknown>;
  response_raw: string | null;
  response_json: Record<string, unknown> | null;
  status: LlmCallStatus;
  http_status: number | null;
  latency_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  error_code: string | null;
}

// ========================
// API Request/Response types
// ========================
export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: 'Bearer';
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface OnboardingRequest {
  timezone: string;
  level: ProfileLevel;
  dictionary_id: number;
}

export interface StartLessonRequest {
  idempotency_key: string;
}

export interface SubmitTranslationRequest {
  exercise_id: number;
  translation: string;
}

export interface ReportSentenceRequest {
  exercise_id: number;
  reason: ReportReason;
  comment?: string;
}

export interface EvaluationResult {
  word_id: number;
  result: 'correct' | 'incorrect' | 'typo';
  user_fragment: string | null;
}

export interface LessonWithExercises {
  lesson: Lesson;
  exercises: LessonExercise[];
}

export interface UserProfile {
  user: User;
  learning_profile: LearningProfile | null;
  stats: {
    words_active: number;
    words_mastered: number;
    lessons_completed: number;
    current_streak: number;
  };
}

// ========================
// Lesson API types
// ========================

/** Слово в preview (упрощённое) */
export interface PreviewWord {
  word_id: number;
  lemma: string;
  pos: Pos;
  translations?: string[];
}

/** Ответ от /lesson/preview */
export interface PreviewData {
  state: 'ready' | 'resume' | 'limit_reached' | 'no_words';
  lesson_number?: number;
  due_words?: PreviewWord[];
  new_words?: PreviewWord[];
  dictionary_exhausted?: boolean;
  // Для state='resume'
  lesson_id?: number;
  exercises_done?: number;
  exercises_total?: number;
  // Для state='limit_reached'
  resets_at?: string;
}

/** Текущее упражнение в уроке */
export interface CurrentExercise {
  exercise_id: number;
  order_index: number;
  sentence: string;
  reference_translation: string;
  target_words?: TargetWord[];
  words?: TargetWord[];
}

/** Результат оценки упражнения */
export interface EvaluateResult {
  exercise_id: number;
  target_sentence: string;
  reference_translation: string;
  user_translation: string | null;
  words: Array<{
    word_id: number;
    lemma: string;
    pos: Pos;
    surface_form: string;
    result: 'correct' | 'typo' | 'incorrect';
    user_fragment: string | null;
    translations: string[];
  }>;
  suggestions: SuggestedWord[];
  lesson_completed: boolean;
}