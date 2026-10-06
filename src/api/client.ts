/**
 * API клиент для 101slovo
 */
import { API_URL } from '../config';

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public code?: string,
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem('access_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // ═══════════════════════════════════════════
  // ИСПРАВЛЕНИЕ: Безопасная склейка URL
  // Убираем trailing slash у baseUrl и гарантируем leading slash у path
  // Это предотвращает ошибку "//auth/login", которую браузер считал доменом
  // ═══════════════════════════════════════════
  const baseUrl = API_URL.endsWith('/') ? API_URL.slice(0, -1) : API_URL;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${baseUrl}${cleanPath}`;

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (response.status === 401) {
    localStorage.removeItem('access_token');
    if (window.location.pathname !== '/') {
      window.location.href = '/';
    }
    throw new ApiError(401, 'Сессия истекла. Пожалуйста, войдите снова.');
  }

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    let code: string | undefined;
    try {
      const errorBody = await response.json();
      detail = errorBody.detail || errorBody.message || detail;
      code = errorBody.code;
    } catch {
      // ignore parse error
    }
    throw new ApiError(response.status, detail, code);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  // ─── Auth ───────────────────────────────────────────────────────
  login(email: string, password: string) {
    return apiRequest<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },
  register(email: string, password: string) {
    return apiRequest<{ access_token: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },
  getMe() {
    return apiRequest<{
      id: number;
      email: string;
      is_onboarded: boolean;
      is_admin: boolean;
      timezone: string | null;
    }>('/auth/me');
  },

  // ─── Lessons ────────────────────────────────────────────────────
  getLessonPreview() {
    return apiRequest<import('../types/database').PreviewData>('/lesson/preview', {
      method: 'POST',
    });
  },
  declineWord(wordId: number) {
    return apiRequest<import('../types/database').PreviewData>('/lesson/new-word/decline', {
      method: 'POST',
      body: JSON.stringify({ word_id: wordId }),
    });
  },
  startLesson(wordIds: number[], idempotencyKey: string) {
    return apiRequest<{
      lesson_id: number;
      lesson_number: number;
      exercises_total: number;
      created: boolean;
      current_exercise: import('../types/database').CurrentExercise;
    }>('/lesson/start', {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify({ word_ids: wordIds }),
    });
  },
  getCurrentExercise(lessonId: number) {
    return apiRequest<{
      lesson_id: number;
      lesson_number: number;
      exercises_done: number;
      exercises_total: number;
      current_exercise: import('../types/database').CurrentExercise;
    }>(`/lesson/${lessonId}/current`);
  },
  evaluateExercise(exerciseId: number, userTranslation: string) {
    return apiRequest<import('../types/database').EvaluateResult>('/lesson/evaluate', {
      method: 'POST',
      body: JSON.stringify({
        exercise_id: exerciseId,
        user_translation: userTranslation,
      }),
    });
  },
  handleSuggestion(exerciseId: number, wordId: number, action: 'add' | 'ignore') {
    return apiRequest<{ status: string; word_id: number; state: string }>(
      `/lesson/exercises/${exerciseId}/suggestions/${wordId}`,
      {
        method: 'POST',
        body: JSON.stringify({ action }),
      },
    );
  },
  getLessonSummary(lessonId: number) {
    return apiRequest<{
      lesson_id: number;
      lesson_number: number;
      exercises_total: number;
      words_total: number;
      correct_count: number;
      incorrect_count: number;
      typo_count: number;
      accuracy: number;
      time_spent: number;
      new_words_learned: number;
      streak_current: number;
      streak_longest: number;
    }>(`/lesson/${lessonId}/summary`);
  },
  reportSentence(exerciseId: number, reason: string, comment?: string) {
    return apiRequest<{ status: string }>(`/lesson/exercises/${exerciseId}/report`, {
      method: 'POST',
      body: JSON.stringify({ reason, comment }),
    });
  },

  // ─── Onboarding ─────────────────────────────────────────────────
  completeOnboarding(
    level: string,
    dictionaryId: number,
    timezone: string,
    wordsPerLesson: number,
    dailyLimit: number
  ) {
    return apiRequest<{ status: string }>('/onboarding/complete', {
      method: 'POST',
      body: JSON.stringify({
        level,
        dictionary_id: dictionaryId,
        timezone,
        words_per_lesson: wordsPerLesson,
        daily_lesson_limit: dailyLimit,
      }),
    });
  },
  getDictionaries() {
    return apiRequest<Array<{
      id: number;
      code: string;
      name: string;
      description: string | null;
    }>>('/onboarding/dictionaries');
  },
  getOnboardingLimits() {
    return apiRequest<{
      words_per_lesson_min: number;
      words_per_lesson_max: number;
      daily_lesson_limit_max: number;
    }>('/onboarding/limits');
  },

  // ─── Settings ───────────────────────────────────────────────────
  getLearningProfile() {
    return apiRequest<{
      level: string;
      dictionary: {
        id: number;
        code: string;
        name: string;
        description: string | null;
      };
      daily_lesson_limit: number;
      daily_lesson_limit_max: number;
      words_per_lesson: number;
      words_per_lesson_min: number;
      words_per_lesson_max: number;
      stats: {
        words: { active: number; mastered: number; ignored: number };
        accuracy_all_time: number;
        accuracy_30_days: number;
        completed_lessons: number;
      };
    }>('/learning-profile');
  },
  updateLearningProfile(data: Record<string, unknown>) {
    return apiRequest<{ status: string }>('/learning-profile', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
  updateTimezone(timezone: string) {
    return apiRequest<{
      today: string;
      lessons_today: number;
      resets_at: string;
      streak: { current: number; longest: number; today_done: boolean };
    }>('/settings/timezone', {
      method: 'PATCH',
      body: JSON.stringify({ timezone }),
    });
  },

  // ─── Profile ────────────────────────────────────────────────────
  getProfileStats() {
    return apiRequest<{
      streak_current: number;
      streak_longest: number;
      words_active: number;
      words_mastered: number;
      words_ignored: number;
      completed_lessons: number;
    }>('/profile/stats');
  },

  // ─── Admin Prompts ──────────────────────────────────────────────
  getPromptsList() {
    return apiRequest<Array<{
      key: string;
      updated_at: string;
      updated_by: number | null;
    }>>('/admin/prompts');
  },
  getPrompt(key: string) {
    return apiRequest<{
      key: string;
      system_template: string;
      required_placeholders: string[];
      updated_at: string;
      updated_by: number | null;
    }>(`/admin/prompts/${key}`);
  },
  updatePrompt(key: string, systemTemplate: string) {
    return apiRequest<{ status: string; key: string }>(`/admin/prompts/${key}`, {
      method: 'PUT',
      body: JSON.stringify({ system_template: systemTemplate }),
    });
  },

  // ─── Admin DB ───────────────────────────────────────────────────
  getDbTables() {
    return apiRequest<Array<{
      table_name: string;
      row_count_estimate: number;
      columns_count: number;
    }>>('/admin/db/tables');
  },
  getDbTableContent(
    tableName: string,
    params: {
      page?: number;
      page_size?: number;
      order_by?: string;
      order_dir?: 'asc' | 'desc';
      search?: string;
    } = {},
  ) {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.append('page', String(params.page));
    if (params.page_size) searchParams.append('page_size', String(params.page_size));
    if (params.order_by) searchParams.append('order_by', params.order_by);
    if (params.order_dir) searchParams.append('order_dir', params.order_dir);
    if (params.search) searchParams.append('search', params.search);
    
    return apiRequest<{
      table_name: string;
      columns: Array<{
        name: string;
        type: string;
        is_primary_key: boolean;
        masked: boolean;
      }>;
      rows: Record<string, unknown>[];
      page: number;
      page_size: number;
      total: number | null;
    }>(`/admin/db/tables/${encodeURIComponent(tableName)}?${searchParams}`);
  },
};

export { ApiError };