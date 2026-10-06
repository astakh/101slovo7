import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { apiClient } from '../api/client';

// ═══════════════════════════════════════════
// Онбординг
// ═══════════════════════════════════════════
export function useCompleteOnboarding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ level, dictionaryId, timezone }: { level: string; dictionaryId: number; timezone: string }) =>
      apiClient.completeOnboarding(level, dictionaryId, timezone),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] });
      qc.invalidateQueries({ queryKey: ['profileStats'] });
      qc.invalidateQueries({ queryKey: ['lessonPreview'] });
      qc.invalidateQueries({ queryKey: ['dictionaries'] });
    },
  });
}

// ═══════════════════════════════════════════
// Профиль и статистика
// ═══════════════════════════════════════════
export function useProfileStats() {
  return useQuery({
    queryKey: ['profileStats'],
    queryFn: apiClient.getProfileStats,
  });
}

export function useProfile() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: apiClient.getLearningProfile,
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => apiClient.updateLearningProfile(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] });
      qc.invalidateQueries({ queryKey: ['profileStats'] });
    },
  });
}

// ═══════════════════════════════════════════
// Уроки
// ═══════════════════════════════════════════
export function useLessonPreview() {
  return useQuery({
    queryKey: ['lessonPreview'],
    queryFn: apiClient.getLessonPreview,
  });
}

export function useDeclineWord() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (wordId: number) => apiClient.declineWord(wordId),
    onSuccess: (data) => {
      qc.setQueryData(['lessonPreview'], data);
    },
  });
}

export function useStartLesson() {
  return useMutation({
    mutationFn: ({ wordIds, idempotencyKey }: { wordIds: number[]; idempotencyKey: string }) =>
      apiClient.startLesson(wordIds, idempotencyKey),
  });
}

export function useCurrentExercise(lessonId: number | undefined) {
  return useQuery({
    queryKey: ['currentExercise', lessonId],
    queryFn: () => apiClient.getCurrentExercise(lessonId!),
    enabled: !!lessonId,
  });
}

export function useEvaluateExercise() {
  return useMutation({
    mutationFn: ({ exerciseId, translation }: { exerciseId: number; translation: string }) =>
      apiClient.evaluateExercise(exerciseId, translation),
  });
}

export function useHandleSuggestion() {
  return useMutation({
    mutationFn: ({ exerciseId, wordId, action }: { exerciseId: number; wordId: number; action: 'add' | 'ignore' }) =>
      apiClient.handleSuggestion(exerciseId, wordId, action),
  });
}

export function useLessonSummary(lessonId: number | undefined) {
  return useQuery({
    queryKey: ['lessonSummary', lessonId],
    queryFn: () => apiClient.getLessonSummary(lessonId!),
    enabled: !!lessonId,
  });
}

// ═══════════════════════════════════════════
// Админ: БД
// ═══════════════════════════════════════════
export function useDbTables() {
  return useQuery({
    queryKey: ['dbTables'],
    queryFn: apiClient.getDbTables,
  });
}

export function useDbTableContent(
  table: string | null,
  params: { page: number; pageSize: number; search: string; orderBy: string | null; orderDir: 'asc' | 'desc' }
) {
  return useQuery({
    queryKey: ['dbTableContent', table, params],
    queryFn: () => apiClient.getDbTableContent(table!, {
      page: params.page,
      page_size: params.pageSize,
      search: params.search,
      order_by: params.orderBy || undefined,
      order_dir: params.orderDir,
    }),
    enabled: !!table,
    placeholderData: keepPreviousData,
  });
}

// ═══════════════════════════════════════════
// Админ: Промпты
// ═══════════════════════════════════════════
export function usePrompts() {
  return useQuery({
    queryKey: ['prompts'],
    queryFn: apiClient.getPromptsList,
  });
}

export function useUpdatePrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ key, template }: { key: string; template: string }) =>
      apiClient.updatePrompt(key, template),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['prompts'] });
    },
  });
}

// ═══════════════════════════════════════════
// Админ: Статистика
// ═══════════════════════════════════════════
export function useAdminStats() {
  return useQuery({
    queryKey: ['adminStats'],
    queryFn: apiClient.getProfileStats,
  });
}

// ═══════════════════════════════════════════
// Жалобы на предложения
// ═══════════════════════════════════════════
export function useReportSentence() {
  return useMutation({
    mutationFn: ({ exerciseId, reason, comment }: { exerciseId: number; reason: string; comment: string }) =>
      apiClient.reportSentence(exerciseId, reason, comment),
  });
}