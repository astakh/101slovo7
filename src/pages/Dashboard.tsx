import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { LogOut, BookOpen, Target, TrendingUp, Settings, Shield } from 'lucide-react';
import { apiClient } from '../api/client';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // React Query берет на себя loading, error, кэширование и рефетч
  const { data: stats, isLoading } = useQuery({
    queryKey: ['profileStats'],
    queryFn: apiClient.getProfileStats,
  });

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  if (!user) return null;
  const isAdmin = user.is_admin === true;

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">101</span>
              </div>
              <span className="font-bold text-xl text-gray-900">slovo</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600 mr-2">{user.email}</span>
              {isAdmin && (
                <Button variant="ghost" onClick={() => navigate('/admin')}>
                  <Shield size={18} /> Админ
                </Button>
              )}
              <Button variant="ghost" onClick={() => navigate('/settings')}>
                <Settings size={18} /> Настройки
              </Button>
              <Button variant="ghost" onClick={handleLogout}>
                <LogOut size={18} /> Выйти
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Добро пожаловать, {user.email.split('@')[0]}! 👋
          </h1>
          <p className="text-gray-600">
            {!user.is_onboarded ? 'Давайте настроим ваш профиль обучения' : 'Готовы продолжить обучение?'}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardContent className="p-6 flex items-center gap-4">
              <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center">
                <BookOpen className="text-indigo-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-600">Слов изучено</p>
                <p className="text-2xl font-bold text-gray-900">
                  {isLoading ? '...' : stats?.words_mastered ?? 0}
                </p>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6 flex items-center gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <Target className="text-green-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-600">Уроков пройдено</p>
                <p className="text-2xl font-bold text-gray-900">
                  {isLoading ? '...' : stats?.completed_lessons ?? 0}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6 flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <TrendingUp className="text-purple-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-600">Текущая серия</p>
                <p className="text-2xl font-bold text-gray-900">
                  {isLoading ? '...' : `${stats?.streak_current ?? 0} дней`}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {!user.is_onboarded ? (
          <Card className="bg-gradient-to-r from-indigo-500 to-purple-500 border-none text-white">
            <CardContent className="p-8">
              <h2 className="text-2xl font-bold mb-2">Настройте профиль обучения</h2>
              <p className="text-indigo-100 mb-6">Выберите уровень и словарь, чтобы начать обучение</p>
              <Button variant="secondary" onClick={() => navigate('/onboarding')}>
                Начать настройку
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="p-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Готовы к уроку?</h2>
              <p className="text-gray-600 mb-6">Начните новый урок или продолжите предыдущий</p>
              <Button size="lg" onClick={() => navigate('/lesson-preview')}>
                Начать урок
              </Button>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}