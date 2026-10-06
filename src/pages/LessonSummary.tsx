import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, CheckCircle2, XCircle, RotateCcw, Trophy, Loader2, AlertCircle, Clock, Target } from 'lucide-react';
import { useLessonSummary } from '../hooks/useApi';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';

export default function LessonSummary() {
  const { lessonId } = useParams<{ lessonId: string }>();
  const navigate = useNavigate();

  const { data: summary, isLoading, error } = useLessonSummary(
    lessonId ? Number(lessonId) : undefined
  );

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="animate-spin text-indigo-600 mx-auto mb-4" size={48} />
          <p className="text-gray-600">Загрузка итогов урока...</p>
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <Card className="p-8 max-w-md text-center">
          <AlertCircle className="text-red-500 mx-auto mb-4" size={48} />
          <h2 className="text-xl font-bold text-gray-900 mb-2">Ошибка</h2>
          <p className="text-gray-600 mb-6">
            {error instanceof Error ? error.message : 'Не удалось загрузить итоги урока'}
          </p>
          <Button onClick={() => navigate('/dashboard')}>На главную</Button>
        </Card>
      </div>
    );
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins} мин ${secs} сек`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center h-16">
          <Button variant="ghost" onClick={() => navigate('/dashboard')}>
            <ArrowLeft size={20} /> На главную
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
          {/* Hero */}
          <div className="text-center">
            <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', delay: 0.2 }}>
              <Trophy className="text-yellow-500 mx-auto mb-4" size={64} />
            </motion.div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Урок {summary.lesson_number} завершён!</h1>
            <p className="text-gray-600">Точность: {summary.accuracy.toFixed(1)}%</p>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-4 text-center">
                <CheckCircle2 className="text-green-500 mx-auto mb-2" size={32} />
                <p className="text-2xl font-bold text-gray-900">{summary.correct_count}</p>
                <p className="text-sm text-gray-600">Верно</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <RotateCcw className="text-yellow-500 mx-auto mb-2" size={32} />
                <p className="text-2xl font-bold text-gray-900">{summary.typo_count}</p>
                <p className="text-sm text-gray-600">С опечатками</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <XCircle className="text-red-500 mx-auto mb-2" size={32} />
                <p className="text-2xl font-bold text-gray-900">{summary.incorrect_count}</p>
                <p className="text-sm text-gray-600">Неверно</p>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Stats */}
          <Card>
            <CardContent className="p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Подробная статистика</h2>
              
              <div className="flex items-center justify-between p-4 bg-indigo-50 rounded-xl">
                <div className="flex items-center gap-3">
                  <Target className="text-indigo-600" size={20} />
                  <span className="text-gray-900 font-medium">Всего слов повторено</span>
                </div>
                <span className="text-xl font-bold text-indigo-600">{summary.words_total}</span>
              </div>

              <div className="flex items-center justify-between p-4 bg-green-50 rounded-xl">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="text-green-600" size={20} />
                  <span className="text-gray-900 font-medium">Новых слов добавлено</span>
                </div>
                <span className="text-xl font-bold text-green-600">{summary.new_words_learned}</span>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                <div className="flex items-center gap-3">
                  <Clock className="text-gray-600" size={20} />
                  <span className="text-gray-900 font-medium">Время урока</span>
                </div>
                <span className="text-xl font-bold text-gray-600">{formatTime(summary.time_spent)}</span>
              </div>
            </CardContent>
          </Card>

          {/* Streak */}
          <div className="grid grid-cols-2 gap-4">
            <Card className="bg-orange-50 border-orange-100">
              <CardContent className="p-6 text-center">
                <p className="text-4xl font-bold text-orange-600 mb-1">{summary.streak_current}</p>
                <p className="text-sm text-gray-600">Текущая серия (дней)</p>
              </CardContent>
            </Card>
            <Card className="bg-purple-50 border-purple-100">
              <CardContent className="p-6 text-center">
                <p className="text-4xl font-bold text-purple-600 mb-1">{summary.streak_longest}</p>
                <p className="text-sm text-gray-600">Лучшая серия (дней)</p>
              </CardContent>
            </Card>
          </div>

          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => navigate('/dashboard')} className="flex-1">
              На главную
            </Button>
            <Button onClick={() => navigate('/lesson-preview')} className="flex-1">
              Следующий урок
            </Button>
          </div>
        </motion.div>
      </main>
    </div>
  );
}