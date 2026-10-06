import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Shield, Database, FileText, BookOpen, Target, TrendingUp } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useProfileStats } from '../hooks/useApi';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  // Используем реальный хук, который возвращает профильную статистику
  const { data: stats, isLoading } = useProfileStats();

  // Guard: только админ
  if (!user?.is_admin) {
    navigate('/dashboard');
    return null;
  }

  const menuItems = [
    { label: 'База данных', icon: Database, path: '/admin/db', color: 'bg-blue-100 text-blue-600' },
    { label: 'Промпты LLM', icon: FileText, path: '/admin/prompts', color: 'bg-purple-100 text-purple-600' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <Button variant="ghost" onClick={() => navigate('/dashboard')}>
            <ArrowLeft size={20} /> Назад
          </Button>
          <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Shield size={20} /> Панель администратора
          </h1>
          <div className="w-20" />
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-8">
        {/* Stats - ИСПРАВЛЕНО: используем реальные поля из getProfileStats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <Card>
            <CardContent className="p-6 flex items-center gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <BookOpen className="text-green-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-600">Изучено слов</p>
                <p className="text-2xl font-bold text-gray-900">
                  {isLoading ? '...' : stats?.words_mastered ?? 0}
                </p>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6 flex items-center gap-4">
              <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center">
                <Target className="text-indigo-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-600">Уроков завершено</p>
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
                <p className="text-sm text-gray-600">Текущий стрик</p>
                <p className="text-2xl font-bold text-gray-900">
                  {isLoading ? '...' : `${stats?.streak_current ?? 0} дн.`}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Menu */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {menuItems.map((item) => (
            <Card
              key={item.path}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => navigate(item.path)}
            >
              <CardContent className="p-6 flex items-center gap-4">
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${item.color}`}>
                  <item.icon size={24} />
                </div>
                <span className="text-lg font-semibold text-gray-900">{item.label}</span>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
}