import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, ArrowRight, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../api/client';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import LevelSelector from '../components/profile/LevelSelector';
import TimezoneSelector from '../components/profile/TimezoneSelector';
import DictionarySelector from '../components/profile/DictionarySelector';
import WordsPerLessonSelector from '../components/profile/WordsPerLessonSelector';
import DailyLimitSelector from '../components/profile/DailyLimitSelector';

export default function Onboarding() {
  const navigate = useNavigate();
  const { user, setUser } = useAuth();

  // Загружаем лимиты из .env бэкенда
  const { data: limits, isLoading: limitsLoading } = useQuery({
    queryKey: ['onboardingLimits'],
    queryFn: apiClient.getOnboardingLimits,
  });

  const [step, setStep] = useState(1);
  const [level, setLevel] = useState('');
  const [dictionaryId, setDictionaryId] = useState<number | null>(null);
  const [timezone, setTimezone] = useState('');
  const [wordsPerLesson, setWordsPerLesson] = useState(5);
  const [dailyLimit, setDailyLimit] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const totalSteps = 5;

  // ИСПРАВЛЕНИЕ: после загрузки лимитов зажимаем начальные значения
  useEffect(() => {
    if (limits) {
      setWordsPerLesson((prev) =>
        Math.max(limits.words_per_lesson_min, Math.min(prev, limits.words_per_lesson_max))
      );
      setDailyLimit((prev) =>
        Math.max(1, Math.min(prev, limits.daily_lesson_limit_max))
      );
    }
  }, [limits]);

  const canProceed = () => {
    if (step === 1) return !!level;
    if (step === 2) return dictionaryId !== null;
    if (step === 3) return !!timezone;
    if (step === 4) return true;
    return true;
  };

  const handleFinish = async () => {
    if (!dictionaryId) return;
    setIsSubmitting(true);
    try {
      await apiClient.completeOnboarding(
        level,
        dictionaryId,
        timezone,
        wordsPerLesson,
        dailyLimit
      );

      if (user) {
        setUser({ ...user, is_onboarded: true, timezone });
      }

      navigate('/dashboard');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Ошибка сохранения');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (limitsLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <Loader2 className="animate-spin text-indigo-600" size={48} />
      </div>
    );
  }

  // Значения лимитов из .env
  const wMin = limits?.words_per_lesson_min ?? 1;
  const wMax = limits?.words_per_lesson_max ?? 10;
  const dMax = limits?.daily_lesson_limit_max ?? 5;

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">
              Шаг {step} из {totalSteps}
            </span>
            {step > 1 && (
              <Button variant="ghost" onClick={() => setStep(step - 1)}>
                <ArrowLeft size={16} /> Назад
              </Button>
            )}
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <motion.div
              className="bg-indigo-600 h-2 rounded-full"
              animate={{ width: `${(step / totalSteps) * 100}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        </div>

        <AnimatePresence mode="wait">
          {step === 1 && (
            <motion.div
              key="s1"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
            >
              <Card>
                <CardContent className="p-8">
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">
                    Ваш уровень английского?
                  </h2>
                  <p className="text-gray-600 mb-6">Выберите наиболее подходящий</p>
                  <LevelSelector value={level} onChange={setLevel} />
                </CardContent>
              </Card>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div
              key="s2"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
            >
              <Card>
                <CardContent className="p-8">
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Какой словарь?</h2>
                  <p className="text-gray-600 mb-6">Выберите тематику для изучения</p>
                  <DictionarySelector value={dictionaryId} onChange={setDictionaryId} />
                </CardContent>
              </Card>
            </motion.div>
          )}

          {step === 3 && (
            <motion.div
              key="s3"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
            >
              <Card>
                <CardContent className="p-8">
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Часовой пояс</h2>
                  <p className="text-gray-600 mb-6">
                    Для корректного подсчёта серий и сброса лимитов
                  </p>
                  <TimezoneSelector value={timezone} onChange={setTimezone} />
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Шаг 4: Ваше упорство */}
          {step === 4 && (
            <motion.div
              key="s4"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
            >
              <Card>
                <CardContent className="p-8 space-y-6">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">Ваше упорство</h2>
                    <p className="text-gray-600 mb-6">
                      Настройте интенсивность обучения под себя
                    </p>
                  </div>

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
                </CardContent>
              </Card>
            </motion.div>
          )}

          {step === 5 && (
            <motion.div
              key="s5"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
            >
              <Card>
                <CardContent className="p-8 text-center">
                  <div className="text-5xl mb-4">🎉</div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Всё готово!</h2>
                  <div className="text-gray-600 mb-6 space-y-1 text-left bg-gray-50 p-4 rounded-xl">
                    <p>
                      🎯 Уровень: <strong>{level}</strong>
                    </p>
                    <p>
                      📚 Слов в уроке: <strong>{wordsPerLesson}</strong>
                    </p>
                    <p>
                      📅 Уроков в день: <strong>{dailyLimit}</strong>
                    </p>
                  </div>
                  <Button
                    size="lg"
                    onClick={handleFinish}
                    isLoading={isSubmitting}
                    className="w-full"
                  >
                    Начать обучение!
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {step < totalSteps && (
          <Button
            size="lg"
            onClick={() => setStep(step + 1)}
            disabled={!canProceed()}
            className="w-full mt-6"
          >
            Далее <ArrowRight size={18} />
          </Button>
        )}
      </div>
    </div>
  );
}