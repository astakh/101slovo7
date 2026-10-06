import { useState, useEffect } from 'react';
import { useNavigate, useLocation, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Send, Loader2, AlertCircle, CheckCircle2, XCircle, RotateCcw, Lightbulb, X, Plus, User, Target, BookOpen } from 'lucide-react';
import { useCurrentExercise, useEvaluateExercise, useHandleSuggestion } from '../hooks/useApi';
import { apiClient } from '../api/client';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { cn } from '../lib/utils';
import type { CurrentExercise, EvaluateResult, TargetWord, SuggestedWord } from '../types/database';

interface LessonState {
  lesson_id: number;
  lesson_number: number;
  exercises: CurrentExercise[];
}

export default function Lesson() {
  const navigate = useNavigate();
  const location = useLocation();
  const { lessonId: paramLessonId } = useParams<{ lessonId: string }>();

  // ═══════════════════════════════════════════
  // ИСПРАВЛЕНИЕ: приоритет paramLessonId (URL) над location.state
  // ═══════════════════════════════════════════
  const resolvedLessonId = paramLessonId
    ? Number(paramLessonId)
    : (location.state as any)?.lessonId || 0;

  const [lesson, setLesson] = useState<LessonState | null>(
    resolvedLessonId > 0
      ? {
          lesson_id: resolvedLessonId,
          lesson_number: (location.state as any)?.lessonNumber || 0,
          exercises: [],
        }
      : null
  );

  const [currentExerciseIndex, setCurrentExerciseIndex] = useState(0);
  const [userTranslation, setUserTranslation] = useState('');
  const [showResult, setShowResult] = useState(false);
  const [result, setResult] = useState<EvaluateResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const activeLessonId = lesson?.lesson_id || (paramLessonId ? Number(paramLessonId) : undefined);

  const { data: exerciseData, isLoading: loadingExercise, error: exerciseError } = useCurrentExercise(
    paramLessonId ? Number(paramLessonId) : undefined
  );

  console.log('[Lesson] 📍 RENDER');
  console.log('[Lesson]   paramLessonId:', paramLessonId);
  console.log('[Lesson]   location.state:', location.state);
  console.log('[Lesson]   resolvedLessonId:', resolvedLessonId);
  console.log('[Lesson]   lesson (state):', lesson);
  console.log('[Lesson]   activeLessonId:', activeLessonId);

  // Обработка ошибки загрузки упражнения (урок уже завершён)
  useEffect(() => {
    if (exerciseError) {
      const err = exerciseError as any;
      const code = err?.code || err?.message || '';
      console.warn('[Lesson] ⚠️ Ошибка useCurrentExercise:', code);

      if (code === 'lesson_not_active' && paramLessonId) {
        navigate(`/lesson/${paramLessonId}/summary`, { replace: true });
      } else if (code === 'lesson_not_found') {
        navigate('/dashboard', { replace: true });
      }
    }
  }, [exerciseError, paramLessonId, navigate]);

  useEffect(() => {
    console.log('[Lesson] 🔄 useEffect: обработка exerciseData');
    console.log('[Lesson]   exerciseData?.current_exercise:', exerciseData?.current_exercise);

    if (!exerciseData?.current_exercise) return;

    if (lesson) {
      console.log('[Lesson] ✅ Обновляем существующий lesson');
      setLesson({ ...lesson, exercises: [exerciseData.current_exercise] });
    } else if (paramLessonId) {
      console.log('[Lesson] ✅ Создаём lesson из paramLessonId');
      setLesson({
        lesson_id: Number(paramLessonId),
        lesson_number: (location.state as any)?.lessonNumber || exerciseData.lesson_number || 0,
        exercises: [exerciseData.current_exercise],
      });
    }
  }, [exerciseData, paramLessonId]);

  const evaluateMutation = useEvaluateExercise();
  const suggestionMutation = useHandleSuggestion();

  const currentExercise = lesson?.exercises?.[currentExerciseIndex];

  const handleEvaluate = async () => {
    console.log('[Lesson] 📤 handleEvaluate');
    if (!currentExercise || !userTranslation.trim()) return;

    setError(null);
    try {
      const data = await evaluateMutation.mutateAsync({
        exerciseId: currentExercise.exercise_id,
        translation: userTranslation,
      });
      setResult(data);
      setShowResult(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка проверки');
    }
  };

  const handleNext = async () => {
    console.log('[Lesson] ➡️ handleNext');
    if (!result) return;

    if (result.lesson_completed) {
      // ═══════════════════════════════════════════
      // ИСПРАВЛЕНИЕ: используем activeLessonId (из URL)
      // ═══════════════════════════════════════════
      navigate(`/lesson/${activeLessonId}/summary`);
      return;
    }

    // ═══════════════════════════════════════════
    // ИСПРАВЛЕНИЕ: используем activeLessonId вместо lesson.lesson_id
    // ═══════════════════════════════════════════
    if (!activeLessonId) {
      console.error('[Lesson] ❌ Нет activeLessonId для загрузки следующего упражнения');
      setError('Не удалось определить ID урока');
      return;
    }

    try {
      console.log('[Lesson] 📦 Загружаем следующее упражнение для lesson_id:', activeLessonId);
      const data = await apiClient.getCurrentExercise(activeLessonId);
      if (!data.current_exercise) throw new Error('Следующее упражнение не найдено');

      setLesson(prev => prev
        ? { ...prev, exercises: [data.current_exercise] }
        : {
            lesson_id: activeLessonId,
            lesson_number: (location.state as any)?.lessonNumber || 0,
            exercises: [data.current_exercise],
          }
      );
      setCurrentExerciseIndex(0);
      setShowResult(false);
      setResult(null);
      setUserTranslation('');
    } catch (err) {
      console.error('[Lesson] ❌ Ошибка загрузки следующего упражнения:', err);
      const apiErr = err as any;
      if (apiErr?.code === 'lesson_not_active' || apiErr?.message === 'lesson_not_active') {
        // Урок завершён — переходим на итоги
        navigate(`/lesson/${activeLessonId}/summary`);
        return;
      }
      setError(err instanceof Error ? err.message : 'Не удалось загрузить следующее упражнение');
    }
  };

  const handleSuggestionAction = async (wordId: number, action: 'add' | 'ignore') => {
    if (!result) return;
    try {
      await suggestionMutation.mutateAsync({
        exerciseId: result.exercise_id,
        wordId,
        action,
      });
      setResult({
        ...result,
        suggestions: result.suggestions?.map((s) =>
          s.word_id === wordId ? { ...s, state: action === 'add' ? 'added' : 'ignored' } : s
        ) || [],
      });
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Ошибка обработки подсказки');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (showResult) handleNext();
      else handleEvaluate();
    }
  };

  if (loadingExercise || (!currentExercise && !error && !exerciseError)) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <Loader2 className="animate-spin text-indigo-600" size={48} />
      </div>
    );
  }

  if (error && !currentExercise) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <Card className="p-8 max-w-md text-center">
          <AlertCircle className="text-red-500 mx-auto mb-4" size={48} />
          <h2 className="text-xl font-bold text-gray-900 mb-2">Ошибка</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <Button onClick={() => navigate('/dashboard')}>На главную</Button>
        </Card>
      </div>
    );
  }

  if (!currentExercise) return null;

  const allCorrect = result?.words.every(w => w.result === 'correct' || w.result === 'typo') ?? false;
  const hasTypos = result?.words.some(w => w.result === 'typo') ?? false;

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <Button variant="ghost" onClick={() => navigate('/dashboard')}>
            <ArrowLeft size={20} />
          </Button>
          <span className="font-semibold text-gray-900">
            Урок {lesson?.lesson_number || ''}
          </span>
          <div className="w-10" />
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <AnimatePresence mode="wait">
          {!showResult ? (
            <motion.div
              key="exercise"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              className="space-y-6"
            >
              <Card>
                <CardContent className="p-8">
                  <p className="text-sm text-gray-500 mb-2">Переведите предложение:</p>
                  <p className="text-xl font-medium text-gray-900 leading-relaxed mb-6">
                    {currentExercise.sentence}
                  </p>

                  {(currentExercise.target_words || currentExercise.words) && (
                    <div className="flex flex-wrap gap-2 mb-6">
                      {(currentExercise.target_words || currentExercise.words || []).map((w: TargetWord) => (
                        <span key={w.word_id} className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-medium">
                          {w.surface_form || w.lemma}
                        </span>
                      ))}
                    </div>
                  )}

                  <textarea
                    value={userTranslation}
                    onChange={(e) => setUserTranslation(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Введите перевод на русский..."
                    rows={3}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none resize-none"
                    autoFocus
                  />

                  {error && (
                    <p className="mt-3 text-sm text-red-600 flex items-center gap-1">
                      <AlertCircle size={14} /> {error}
                    </p>
                  )}

                  <Button
                    onClick={handleEvaluate}
                    disabled={!userTranslation.trim()}
                    isLoading={evaluateMutation.isPending}
                    className="w-full mt-4"
                    size="lg"
                  >
                    <Send size={18} /> Проверить
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          ) : result ? (
            <motion.div
              key="result"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              className="space-y-6"
            >
              <div className="flex items-center gap-3 p-4 bg-white rounded-xl shadow-sm border border-gray-200">
                {allCorrect && !hasTypos && <CheckCircle2 className="text-green-500" size={32} />}
                {hasTypos && <RotateCcw className="text-yellow-500" size={32} />}
                {!allCorrect && <XCircle className="text-red-500" size={32} />}
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    {allCorrect && !hasTypos && 'Отлично!'}
                    {hasTypos && 'Почти верно!'}
                    {!allCorrect && 'Есть ошибки'}
                  </h2>
                  <p className="text-sm text-gray-500">Разберите результаты ниже</p>
                </div>
              </div>

              <Card>
                <CardContent className="p-6">
                  <p className="text-sm text-gray-500 mb-2 flex items-center gap-2">
                    <BookOpen size={16} /> Исходное предложение
                  </p>
                  <p className="text-xl font-medium text-gray-900 leading-relaxed">
                    {result.target_sentence}
                  </p>
                </CardContent>
              </Card>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className={cn(
                  'border-2',
                  allCorrect && !hasTypos ? 'border-green-200 bg-green-50' :
                  hasTypos ? 'border-yellow-200 bg-yellow-50' : 'border-red-200 bg-red-50'
                )}>
                  <CardContent className="p-6">
                    <p className="text-sm text-gray-500 mb-2 flex items-center gap-2">
                      <User size={16} /> Ваш перевод
                    </p>
                    <p className="text-gray-900 font-medium">{result.user_translation}</p>
                  </CardContent>
                </Card>

                <Card className="border-2 border-indigo-200 bg-indigo-50">
                  <CardContent className="p-6">
                    <p className="text-sm text-gray-500 mb-2 flex items-center gap-2">
                      <CheckCircle2 size={16} /> Правильный перевод
                    </p>
                    <p className="text-gray-900 font-medium">{result.reference_translation}</p>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardContent className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <Target size={20} /> Целевые слова
                  </h3>
                  <div className="space-y-3">
                    {result.words.map((w) => (
                      <div
                        key={w.word_id}
                        className={cn(
                          'p-4 rounded-xl border',
                          w.result === 'correct' && 'bg-green-50 border-green-200',
                          w.result === 'typo' && 'bg-yellow-50 border-yellow-200',
                          w.result === 'incorrect' && 'bg-red-50 border-red-200'
                        )}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-gray-900">{w.lemma}</span>
                            <span className="text-sm text-gray-500">({w.surface_form})</span>
                          </div>
                          <div className="flex items-center gap-2">
                            {w.result === 'correct' && <><CheckCircle2 className="text-green-600" size={20} /> <span className="text-green-700 font-medium text-sm">Верно</span></>}
                            {w.result === 'typo' && <><RotateCcw className="text-yellow-600" size={20} /> <span className="text-yellow-700 font-medium text-sm">Опечатка</span></>}
                            {w.result === 'incorrect' && <><XCircle className="text-red-600" size={20} /> <span className="text-red-700 font-medium text-sm">Неверно</span></>}
                          </div>
                        </div>
                        {w.result === 'incorrect' && (
                          <div className="mt-3 space-y-2 text-sm border-t border-red-200 pt-3">
                            <div className="flex items-start gap-2">
                              <span className="text-red-600 font-semibold min-w-[110px]">Ваш перевод:</span>
                              <span className="text-red-800">{w.user_fragment || '—'}</span>
                            </div>
                            <div className="flex items-start gap-2">
                              <span className="text-green-600 font-semibold min-w-[110px]">Правильно:</span>
                              <span className="text-green-800">{w.translations.join(', ')}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {result.suggestions && result.suggestions.length > 0 && (
                <Card>
                  <CardContent className="p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
                      <Lightbulb size={20} /> Слова для добавления в словарь
                    </h3>
                    <p className="text-sm text-gray-500 mb-4">
                      Эти слова встретились в предложении, но не являются целевыми. Вы можете добавить их в свой словарь.
                    </p>
                    <div className="space-y-3">
                      {result.suggestions.map((s) => (
                        <div key={s.word_id} className="p-4 bg-amber-50 rounded-xl border border-amber-200">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-bold text-gray-900">{s.lemma}</span>
                                {s.suggestion_type === 'error' && (
                                  <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">ошибка перевода</span>
                                )}
                                {s.suggestion_type === 'new' && (
                                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">новое слово</span>
                                )}
                              </div>
                              <div className="text-sm text-gray-700 mb-2">
                                <span className="font-medium">Перевод:</span> {s.translations.join(', ')}
                              </div>
                              {s.suggestion_type === 'error' && s.user_fragment && (
                                <div className="text-sm text-red-700">
                                  <span className="font-medium">Ваш перевод:</span> {s.user_fragment}
                                </div>
                              )}
                            </div>
                            <div className="flex flex-col gap-2">
                              {s.state === 'suggested' ? (
                                <Button
                                  size="default"
                                  onClick={() => handleSuggestionAction(s.word_id, 'add')}
                                  disabled={suggestionMutation.isPending}
                                  isLoading={suggestionMutation.isPending}
                                >
                                  <Plus size={16} /> Добавить
                                </Button>
                              ) : s.state === 'added' ? (
                                <div className="flex items-center gap-1 text-green-600 text-sm font-medium px-3 py-2">
                                  <CheckCircle2 size={16} /> Добавлено
                                </div>
                              ) : (
                                <div className="flex items-center gap-1 text-gray-400 text-sm font-medium px-3 py-2">
                                  <X size={16} /> Пропущено
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              <Button onClick={handleNext} size="lg" className="w-full">
                {result.lesson_completed ? 'Завершить урок' : 'Следующее упражнение →'}
              </Button>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </main>
    </div>
  );
}