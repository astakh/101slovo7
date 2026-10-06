import { Check } from 'lucide-react';
import { cn } from '../../lib/utils';

export const LEVELS = [
  { code: 'A1', name: 'A1', desc: 'Начальный' },
  { code: 'A2', name: 'A2', desc: 'Элементарный' },
  { code: 'B1', name: 'B1', desc: 'Средний' },
  { code: 'B2', name: 'B2', desc: 'Выше среднего' },
  { code: 'C1', name: 'C1', desc: 'Продвинутый' },
  { code: 'C2', name: 'C2', desc: 'Эксперт' },
];

interface LevelSelectorProps {
  value: string;
  onChange: (level: string) => void;
}

export default function LevelSelector({ value, onChange }: LevelSelectorProps) {
  return (
    <div className="space-y-3">
      {LEVELS.map((l) => (
        <button
          key={l.code}
          type="button"
          onClick={() => onChange(l.code)}
          className={cn(
            'w-full p-4 rounded-xl border-2 text-left transition-all flex items-center justify-between',
            value === l.code
              ? 'border-indigo-500 bg-indigo-50'
              : 'border-gray-200 hover:border-gray-300'
          )}
        >
          <div>
            <span className="font-bold text-gray-900">{l.name}</span>
            <span className="ml-2 text-gray-600">— {l.desc}</span>
          </div>
          {value === l.code && <Check className="text-indigo-600" size={20} />}
        </button>
      ))}
    </div>
  );
}