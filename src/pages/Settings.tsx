import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Save, Loader2, Check, Shield } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useProfile } from '../hooks/useApi';
import { apiClient } from '../api/client';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import LevelSelector from '../components/profile/LevelSelector';
import TimezoneSelector from '../components/profile/TimezoneSelector';
import DictionarySelector from '../components/profile/DictionarySelector';
import WordsPerLessonSelector from '../components/profile/WordsPerLessonSelector';
import DailyLimitSelector from '../components/profile/DailyLimitSelector';

export default function Settings() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, setUser } = useAuth();
  const { data: profile, isLoading } = useProfile();

  const [level, setLevel] = useState('');
  const [dictionaryId, setDictionaryId] = useState<number | null>(null);
  const [timezone, setTimezone] = useState('');
  const [wordsPerLesson, setWordsPerLesson] = useState(5);
  const [dailyLimit, setDailyLimit] = useState(1);
  const [saved, setSaved] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (profile) {
      setLevel(profile.level || '');
      setDictionaryId(profile.dictionary?.id || null);

      // ИСПРАВЛЕНИЕ: clamp значений из БД в допустимые пределы из .env
      // Если в БД хранится старое значение (например, 10), а лимит теперь 5,
      // мы зажимаем до 5, чтобы не получить 422 при сохранении.
      const wMin = profile.words_per_lesson_min ?? 1;
      const wMax = profile.words_per_lesson_max ?? 10;
      const dMax = profile.daily_lesson_limit_max ?? 5;

      const clampedWords = Math.max(wMin, Math.min(profile.words_per_lesson ?? 5, wMax));
      const clampedDaily = Math.max(1, Math.min(profile.daily_lesson_limit ?? 1, dMax));

      setWordsPerLesson(clampedWords);
      setDailyLimit(clampedDaily);
    }
    if (user) {
      setTimezone(user.timezone || '');
    }
  }, [profile, user]);

  const handleSave = async () => {
    if (!dictionaryId) {
      alert('Пожалуйста, выберите словарь');
      return;
    }

    setIsSubmitting(true);
    try {
      // 1. Обновляем профиль обучения (level, dictionary, limits)
      await apiClient.updateLearningProfile({
        level,
        dictionary_id: dictionaryId,
        words_per_lesson: wordsPerLesson,
        daily_lesson_limit: dailyLimit,
      });

      // 2. Обновляем часовой пояс (если он изменился)
      if (timezone && timezone !== user?.timezone) {
        await apiClient.updateTimezone(timezone);
        if (user) {
          setUser({ ...user, timezone });
        }
      }

      setSaved(true);
      setTimeout(() => setSaved(false), 2000);

      queryClient.invalidateQueries({ queryKey: ['profile'] });
      queryClient.invalidateQueries({ queryKey: ['profileStats'] });
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Ошибка сохранения');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <Loader2 className="animate-spin text-indigo-600" size={48} />
      </div>
    );
  }

  // Лимиты из профиля (которые бэкенд взял из .env)
  const wMin = profile?.words_per_lesson_min ?? 1;
  const wMax = profile?.words_per_lesson_max ?? 10;
  const dMax = profile?.daily_lesson_limit_max ?? 5;

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <Button variant="ghost" onClick={() => navigate('/dashboard')}>
            <ArrowLeft size={20} /> Назад
          </Button>
          <h1 className="text-lg font-bold text-gray-900">Настройки</h1>
          {user?.is_admin ? (
            <Button variant="ghost" onClick={() => navigate('/admin')}>
              <Shield size={18} /> Админ
            </Button>
          ) : <div className="w-20" />}
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-6">
        <Card>
          <CardHeader><CardTitle>Уровень английского</CardTitle></CardHeader>
          <CardContent><LevelSelector value={level} onChange={setLevel} /></CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Словарь</CardTitle></CardHeader>
          <CardContent><DictionarySelector value={dictionaryId} onChange={setDictionaryId} /></CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Интенсивность обучения</CardTitle></CardHeader>
          <CardContent className="space-y-6">
            <WordsPerLessonSelector
              value={wordsPerLesson}
              onChange={setWordsPerLesson}
              min={wMin}
              max={wMax}
            />
            <DailyLimitSelector
              value={dailyLimit}
              onChange={setDailyLimit}
              max={dMax}
            />
            <p className="text-xs text-gray-500">
              💡 Эти лимиты помогают учиться регулярно и не перегорать. Максимальные значения заданы в настройках приложения.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Часовой пояс</CardTitle></CardHeader>
          <CardContent>
            <TimezoneSelector value={timezone} onChange={setTimezone} />
            <p className="text-xs text-gray-500 mt-2">
              ⚠️ Внимание: смена часового пояса возможна не чаще одного раза в 7 дней.
            </p>
          </CardContent>
        </Card>

        <Button
          size="lg"
          onClick={handleSave}
          isLoading={isSubmitting}
          className="w-full"
        >
          {saved ? (
            <><Check size={20} /> Сохранено!</>
          ) : (
            <><Save size={20} /> Сохранить изменения</>
          )}
        </Button>
      </main>
    </div>
  );
}