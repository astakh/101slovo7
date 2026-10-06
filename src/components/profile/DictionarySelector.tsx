import { useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { apiClient } from '../../api/client';
import { cn } from '../../lib/utils';

// Маппинг иконок для известных кодов словарей
const ICONS: Record<string, string> = {
  general: '📚',
  business: '💼',
  travel: '✈️',
  it: '💻',
  default: '📖',
};

interface DictionarySelectorProps {
  value: number | null;
  onChange: (id: number) => void;
}

export default function DictionarySelector({ value, onChange }: DictionarySelectorProps) {
  const { data: dictionaries, isLoading } = useQuery({
    queryKey: ['dictionaries'],
    queryFn: apiClient.getDictionaries,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="animate-spin text-indigo-600" size={32} />
      </div>
    );
  }

  if (!dictionaries || dictionaries.length === 0) {
    return <p className="text-gray-500 text-center py-4">Словари не найдены</p>;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {dictionaries.map((d) => (
        <button
          key={d.id}
          type="button"
          onClick={() => onChange(d.id)}
          className={cn(
            'p-4 rounded-xl border-2 text-left transition-all',
            value === d.id
              ? 'border-indigo-500 bg-indigo-50'
              : 'border-gray-200 hover:border-gray-300'
          )}
        >
          <div className="text-2xl mb-2">{ICONS[d.code] || ICONS.default}</div>
          <div className="font-semibold text-gray-900">{d.name}</div>
          <div className="text-sm text-gray-600">{d.description || 'Описание отсутствует'}</div>
        </button>
      ))}
    </div>
  );
}