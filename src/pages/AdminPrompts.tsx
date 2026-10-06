// src/pages/AdminPrompts.tsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Loader2, AlertCircle, CheckCircle2, FileText, Shield } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../api/client';
import { cn } from '../lib/utils'; // ИСПРАВЛЕНО: добавлен импорт cn

export default function AdminPrompts() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [prompts, setPrompts] = useState<any[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [promptData, setPromptData] = useState<any>(null);
  const [editText, setEditText] = useState('');
  const [loadingList, setLoadingList] = useState(true);
  const [loadingPrompt, setLoadingPrompt] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.is_admin) {
      navigate('/dashboard');
      return;
    }
    loadPromptsList();
  }, [user]);

  const loadPromptsList = async () => {
    setLoadingList(true);
    try {
      // ИСПРАВЛЕНО: убрана передача token, apiClient берёт его сам
      const data = await apiClient.getPromptsList();
      setPrompts(data);
    } catch (err) {
      setError('Не удалось загрузить список промптов');
    } finally {
      setLoadingList(false);
    }
  };

  const loadPrompt = async (key: string) => {
    setSelectedKey(key);
    setLoadingPrompt(true);
    setError(null);
    setSuccess(null);
    try {
      // ИСПРАВЛЕНО: убрана передача token
      const data = await apiClient.getPrompt(key);
      setPromptData(data);
      setEditText(data.system_template);
    } catch (err) {
      setError('Не удалось загрузить текст промпта');
    } finally {
      setLoadingPrompt(false);
    }
  };

  const handleSave = async () => {
    // ИСПРАВЛЕНО: добавлена проверка на null
    if (!selectedKey) return;
    
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      // ИСПРАВЛЕНО: убрана передача token
      await apiClient.updatePrompt(selectedKey, editText);
      setSuccess('Промпт успешно сохранён и применён!');
      loadPromptsList();
    } catch (err: any) {
      setError(err.message || 'Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  if (!user?.is_admin) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft size={20} />
              <span>Назад</span>
            </button>
            <div className="ml-4 flex items-center gap-2">
              <Shield className="text-red-500" size={24} />
              <h1 className="text-xl font-bold text-gray-900">Управление промптами LLM</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Prompts List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4 sticky top-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Список промптов</h2>
              {loadingList ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="animate-spin text-indigo-600" size={32} />
                </div>
              ) : (
                <div className="space-y-2">
                  {prompts.map((p) => (
                    <button
                      key={p.key}
                      onClick={() => loadPrompt(p.key)}
                      className={cn(
                        'w-full text-left p-3 rounded-lg border transition-all',
                        selectedKey === p.key
                          ? 'border-indigo-500 bg-indigo-50 ring-2 ring-indigo-200'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      )}
                    >
                      <div className="font-mono text-sm font-semibold text-gray-800 break-all">{p.key}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        {new Date(p.updated_at).toLocaleString('ru-RU')}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right: Editor */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              {loadingPrompt ? (
                <div className="flex justify-center py-16">
                  <Loader2 className="animate-spin text-indigo-600" size={48} />
                </div>
              ) : promptData ? (
                <div className="space-y-6">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900 font-mono">{promptData.key}</h2>
                    <p className="text-sm text-gray-500 mt-1">
                      Обязательные плейсхолдеры:{' '}
                      <span className="font-mono text-indigo-600 font-semibold">
                        {promptData.required_placeholders.length > 0
                          ? promptData.required_placeholders.map((p: string) => `{${p}}`).join(', ')
                          : 'нет'}
                      </span>
                    </p>
                  </div>

                  {error && (
                    <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-start gap-2">
                      <AlertCircle size={20} className="flex-shrink-0 mt-0.5" />
                      <span className="font-mono">{error}</span>
                    </div>
                  )}

                  {success && (
                    <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm flex items-start gap-2">
                      <CheckCircle2 size={20} className="flex-shrink-0 mt-0.5" />
                      <span>{success}</span>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Системный шаблон (System Template)
                    </label>
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      rows={20}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all font-mono text-sm resize-y bg-gray-50"
                      placeholder="Введите текст промпта..."
                    />
                    <div className="flex justify-between mt-2 text-xs text-gray-500">
                      <span>
                        Используйте плейсхолдеры: <code className="bg-gray-100 px-1 rounded">{'{level}'}</code>
                      </span>
                      <span className={editText.length > 8000 ? 'text-red-500 font-bold' : ''}>
                        {editText.length} / 8000 символов
                      </span>
                    </div>
                  </div>

                  <div className="flex justify-end pt-4 border-t border-gray-100">
                    <button
                      onClick={handleSave}
                      disabled={saving || editText.length === 0 || editText.length > 8000}
                      className="px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 shadow-md shadow-indigo-200"
                    >
                      {saving ? (
                        <>
                          <Loader2 className="animate-spin" size={20} />
                          Сохранение...
                        </>
                      ) : (
                        <>
                          <Save size={20} />
                          Сохранить промпт
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-gray-400">
                  <FileText size={48} className="mb-4" />
                  <p>Выберите промпт из списка слева для редактирования</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}