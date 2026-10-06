import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BookOpen, Brain, Target, Zap, ArrowRight, X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';

const HOW_IT_WORKS_STEPS = [
  { number: '01', title: 'Выберите слова', description: 'Алгоритм подберёт новые слова и повторения по SRS.' },
  { number: '02', title: 'Прочитайте контекст', description: 'Нейросеть создаст предложение с целевыми словами.' },
  { number: '03', title: 'Переведите', description: 'Введите перевод предложения на русский язык.' },
  { number: '04', title: 'Получи результат', description: 'Нейросеть проверит перевод, а алгоритм запланирует повторение.' },
];

const FEATURES = [
  { icon: Brain, title: 'Интервальное повторение', desc: 'SRS-алгоритм с 6 стадиями запоминания' },
  { icon: BookOpen, title: 'Контекстное обучение', desc: 'Слова в живых предложениях от LLM' },
  { icon: Target, title: 'Точная проверка', desc: 'GigaChat оценивает перевод с учётом опечаток' },
  { icon: Zap, title: 'Быстрые уроки', desc: '5-10 минут в день для стабильного прогресса' },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isInitializing } = useAuth();
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('register');

  useEffect(() => {
    if (!isInitializing && isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isInitializing, isAuthenticated, navigate]);

  if (isInitializing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-purple-50">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-2xl flex items-center justify-center mx-auto mb-4 animate-pulse">
            <span className="text-white font-bold text-xl">101</span>
          </div>
          <p className="text-gray-500">Загрузка...</p>
        </div>
      </div>
    );
  }

  const openAuth = (mode: 'login' | 'register') => {
    setAuthMode(mode);
    setAuthModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">101</span>
            </div>
            <span className="font-bold text-xl text-gray-900">slovo</span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={() => openAuth('login')}>Войти</Button>
            <Button onClick={() => openAuth('register')}>Начать бесплатно</Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="py-24 bg-gradient-to-br from-indigo-50 via-white to-purple-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-4xl sm:text-6xl font-bold text-gray-900 mb-6">
              Учите английские слова<br />
              <span className="bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                в контексте
              </span>
            </h1>
            <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
              Нейросеть создаёт предложения с новыми словами, а алгоритм интервального повторения помогает запомнить их навсегда.
            </p>
            <Button size="lg" onClick={() => openAuth('register')}>
              Начать обучение <ArrowRight size={20} />
            </Button>
          </motion.div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">Как это работает</h2>
            <p className="mt-4 text-lg text-gray-600">Четыре шага к новому слову</p>
          </motion.div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {HOW_IT_WORKS_STEPS.map((step, idx) => (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1 }}
              >
                <Card className="h-full">
                  <CardContent className="p-6">
                    <span className="text-3xl font-bold text-indigo-200">{step.number}</span>
                    <h3 className="text-lg font-semibold text-gray-900 mt-2 mb-2">{step.title}</h3>
                    <p className="text-gray-600">{step.description}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">Почему 101slovo?</h2>
          </motion.div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {FEATURES.map((f, idx) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1 }}
              >
                <Card className="h-full">
                  <CardContent className="p-6 text-center">
                    <f.icon className="text-indigo-600 mx-auto mb-4" size={32} />
                    <h3 className="font-semibold text-gray-900 mb-2">{f.title}</h3>
                    <p className="text-sm text-gray-600">{f.desc}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 bg-gradient-to-r from-indigo-600 to-purple-600">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">Готовы начать?</h2>
          <p className="text-indigo-100 text-lg mb-8">Присоединяйтесь и учите слова эффективно</p>
          <Button variant="secondary" size="lg" onClick={() => openAuth('register')}>
            Создать аккаунт бесплатно
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 bg-gray-900 text-gray-400 text-center text-sm">
        © {new Date().getFullYear()} 101slovo. Все права защищены.
      </footer>

      {/* Auth Modal */}
      {authModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="w-full max-w-md">
            <Card>
              <CardContent className="p-8">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold text-gray-900">
                    {authMode === 'login' ? 'Вход' : 'Регистрация'}
                  </h2>
                  <Button variant="ghost" size="icon" onClick={() => setAuthModalOpen(false)}>
                    <X size={20} />
                  </Button>
                </div>
                <AuthForm mode={authMode} onToggle={() => setAuthMode(authMode === 'login' ? 'register' : 'login')} />
              </CardContent>
            </Card>
          </motion.div>
        </div>
      )}
    </div>
  );
}

/* Встроенная форма авторизации (можно вынести в отдельный компонент) */
function AuthForm({ mode, onToggle }: { mode: 'login' | 'register'; onToggle: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(email, password);
      }
      navigate('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Пароль</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={6}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
        />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <Button type="submit" isLoading={loading} className="w-full">
        {mode === 'login' ? 'Войти' : 'Зарегистрироваться'}
      </Button>
      <p className="text-center text-sm text-gray-600">
        {mode === 'login' ? 'Нет аккаунта?' : 'Уже есть аккаунт?'}{' '}
        <button type="button" onClick={onToggle} className="text-indigo-600 hover:underline font-medium">
          {mode === 'login' ? 'Зарегистрироваться' : 'Войти'}
        </button>
      </p>
    </form>
  );
}