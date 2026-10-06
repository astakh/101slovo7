import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, BookOpen, X, Check, Loader2, AlertCircle } from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { useStartLesson } from '../hooks/useApi';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import type { PreviewData } from '../types/database';

const POS_LABELS: Record<string, string> = {
  noun: 'существительное', verb: 'глагол', adj: 'прилагательное', adv: 'наречие',
  pron: 'местоимение', prep: 'предлог', conj: 'союз', num: 'числительное',
  det: 'определитель', intj: 'междометие',
};

export default function LessonPreview() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [decliningWords, setDecliningWords] = useState<Set<number>>(new Set());
  const [startError, setStartError] = useState<string | null>(null);
  const startLessonMutation = useStartLesson();

  // <-- ДОБАВЛЕНО: извлекаем refetch из useQuery
  const { data: preview, isLoading, error, refetch } = useQuery({
    queryKey: ['lessonPreview'],
    queryFn: apiClient.getLessonPreview,
  });

  const handleDeclineWord = async (wordId: number) => {
    setDecliningWords(prev => new Set(prev).add(wordId));
    try {
      const updatedPreview = await apiClient.declineWord(wordId);
      queryClient.setQueryData(['lessonPreview'], updatedPreview);
    } catch (err) {
      console.error(err);
      alert(err instanceof Error ? err.message : 'Ошибка отказа от слова');
    } finally {
      setDecliningWords(prev => {
        const next = new Set(prev);
        next.delete(wordId);
        return next;
      });
    }
  };

  const handleStartLesson = async () => {
    console.log('[LessonPreview] 🚀 Кнопка "Начать урок" нажата');
    setStartError(null);
    
    try {
      // 1. ПРИНУДИТЕЛЬНО запрашиваем свежие данные с бэкенда прямо перед стартом
      const freshPreview = await refetch().then(res => res.data);
      
      if (!freshPreview) {
        console.warn('[LessonPreview] ❌ preview is null after refetch');
        return;
      }

      // 2. Берем word_ids ТОЛЬКО из свежих данных
      const wordIds = [
        ...(freshPreview.due_words?.map(w => w.word_id) || []),
        ...(freshPreview.new_words?.map(w => w.word_id) || []),
      ];

      console.log('[LessonPreview] 📦 wordIds для отправки (FRESH):', wordIds);
      
      if (wordIds.length === 0) {
        setStartError('Нет слов для начала урока.');
        return;
      }

      const idempotencyKey = (typeof crypto !== 'undefined' && crypto.randomUUID)
        ? crypto.randomUUID()
        : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
            const r = (Math.random() * 16) | 0;
            const v = c === 'x' ? r : (r & 0x3) | 0x8;
            return v.toString(16);
          });

      console.log('[LessonPreview] 🔑 Idempotency-Key:', idempotencyKey);
      console.log('[LessonPreview] ⏳ Отправляем запрос на backend (ожидание LLM)...');
      
      const response = await startLessonMutation.mutateAsync({ wordIds, idempotencyKey });
      
      console.log('[LessonPreview] ✅ Урок успешно создан:', response);
      console.log('[LessonPreview] 🆔 Новый lesson_id:', response.lesson_id);
      
      navigate(`/lesson/${response.lesson_id}`, {
        state: {
          lessonId: response.lesson_id,
          lessonNumber: response.lesson_number,
        },
      });
    } catch (err) {
      console.error('[LessonPreview] ❌ Ошибка при создании урока:', err);
      let errorMsg = 'Не удалось начать урок. Попробуйте ещё раз.';
      if (err instanceof Error) {
        const msg = err.message;
        if (msg === 'resume_available') errorMsg = 'У вас уже есть незавершённый урок. Вернитесь на главную, чтобы продолжить его.';
        else if (msg === 'limit_reached') errorMsg = 'Вы достигли дневного лимита уроков. Возвращайтесь завтра!';
        else if (msg === 'preview_outdated') errorMsg = 'Список слов устарел. Пожалуйста, обновите страницу.';
        else if (msg.includes('llm')) errorMsg = 'Нейросеть временно недоступна. Попробуйте через минуту.';
        else errorMsg = msg;
      }
      setStartError(errorMsg);
    }
  };

  const handleResumeLesson = () => {
    if (!preview || !preview.lesson_id) return;
    navigate(`/lesson/${preview.lesson_id}`, {
      state: {
        lessonId: preview.lesson_id,
        lessonNumber: preview.lesson_number,
      },
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <Loader2 className="animate-spin text-indigo-600" size={48} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <Card className="p-8 max-w-md text-center">
          <AlertCircle className="text-red-500 mx-auto mb-4" size={48} />
          <h2 className="text-xl font-bold text-gray-900 mb-2">Ошибка</h2>
          <p className="text-gray-600 mb-6">{(error as Error).message}</p>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => navigate('/dashboard')} className="flex-1">Назад</Button>
            <Button onClick={() => refetch()} className="flex-1">Повторить</Button>
          </div>
        </Card>
      </div>
    );
  }

  if (!preview) return null;

  if (preview.state === 'resume' || preview.state === 'limit_reached' || preview.state === 'no_words') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center h-16">
            <Button variant="ghost" onClick={() => navigate('/dashboard')}>
              <ArrowLeft size={20} /> Назад
            </Button>
          </div>
        </header>
        <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <Card className="p-8 text-center">
            {preview.state === 'resume' && (
              <>
                <BookOpen className="text-indigo-600 mx-auto mb-4" size={48} />
                <h2 className="text-2xl font-bold text-gray-900 mb-2">У вас есть незавершённый урок</h2>
                <p className="text-gray-600 mb-6">Упражнение {preview.exercises_done} из {preview.exercises_total}</p>
                <div className="flex gap-3 justify-center">
                  <Button variant="secondary" onClick={() => navigate('/dashboard')}>На главную</Button>
                  <Button onClick={handleResumeLesson}>Продолжить урок</Button>
                </div>
              </>
            )}
            {preview.state === 'limit_reached' && (
              <>
                <AlertCircle className="text-yellow-600 mx-auto mb-4" size={48} />
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Дневной лимит исчерпан</h2>
                <p className="text-gray-600 mb-6">Вы достигли лимита уроков на сегодня. Возвращайтесь завтра!</p>
                <Button onClick={() => navigate('/dashboard')}>На главную</Button>
              </>
            )}
            {preview.state === 'no_words' && (
              <>
                <BookOpen className="text-gray-400 mx-auto mb-4" size={48} />
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Нет слов для изучения</h2>
                <p className="text-gray-600 mb-6">
                  {preview.dictionary_exhausted ? 'Словарь исчерпан.' : 'Все слова уже изучены.'}
                </p>
                <Button onClick={() => navigate('/dashboard')}>На главную</Button>
              </>
            )}
          </Card>
        </main>
      </div>
    );
  }

  const dueWords = preview.due_words || [];
  const newWords = preview.new_words || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <Button variant="ghost" onClick={() => navigate('/dashboard')}>
            <ArrowLeft size={20} /> Назад
          </Button>
          <div className="flex items-center gap-2">
            <BookOpen className="text-indigo-600" size={20} />
            <span className="font-semibold text-gray-900">Урок {preview.lesson_number}</span>
          </div>
          <div className="w-20" />
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Слова для урока</h1>
            <p className="text-gray-600">Проверьте список слов перед началом урока.</p>
          </div>

          {dueWords.length > 0 && (
            <Card>
              <CardContent className="p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <span className="text-blue-600">🔄</span> Повторение ({dueWords.length})
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {dueWords.map(word => (
                    <div key={word.word_id} className="p-4 bg-blue-50 rounded-xl border border-blue-100">
                      <div className="font-semibold text-gray-900">{word.lemma}</div>
                      <div className="text-sm text-gray-600">{POS_LABELS[word.pos] || word.pos}</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {newWords.length > 0 && (
            <Card>
              <CardContent className="p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <span className="text-green-600">✨</span> Новые слова ({newWords.length})
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {newWords.map(word => (
                    <motion.div key={word.word_id} layout className="p-4 bg-green-50 rounded-xl border border-green-100 flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-semibold text-gray-900">{word.lemma}</div>
                        <div className="text-sm text-gray-600 mb-2">{POS_LABELS[word.pos] || word.pos}</div>
                        {word.translations && <div className="text-sm text-gray-700">{word.translations.join(', ')}</div>}
                      </div>
                      <button
                        onClick={() => handleDeclineWord(word.word_id)}
                        disabled={decliningWords.has(word.word_id)}
                        className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                      >
                        {decliningWords.has(word.word_id) ? <Loader2 className="animate-spin" size={18} /> : <X size={18} />}
                      </button>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {preview.dictionary_exhausted && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-800">
              ⚠️ В словаре недостаточно слов. Будет использовано {dueWords.length + newWords.length} слов.
            </div>
          )}

          {startError && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-800 flex items-center gap-2">
              <AlertCircle size={18} className="flex-shrink-0" />
              <span className="flex-1">{startError}</span>
              <button onClick={() => setStartError(null)} className="text-red-500 hover:text-red-700">
                <X size={16} />
              </button>
            </div>
          )}

          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => navigate('/dashboard')} className="flex-1">Отмена</Button>
            <Button
              onClick={handleStartLesson}
              disabled={dueWords.length + newWords.length === 0 || startLessonMutation.isPending}
              isLoading={startLessonMutation.isPending}
              className="flex-1"
            >
              <Check size={20} /> Начать урок ({dueWords.length + newWords.length} слов)
            </Button>
          </div>
        </motion.div>
      </main>
    </div>
  );
}