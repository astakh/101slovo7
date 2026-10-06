import { CalendarCheck } from 'lucide-react';

interface DailyLimitSelectorProps {
  value: number;
  onChange: (val: number) => void;
  min?: number;
  max?: number;
}

export default function DailyLimitSelector({ 
  value, 
  onChange, 
  min = 1, 
  max = 5 
}: DailyLimitSelectorProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between p-4 bg-purple-50 rounded-xl border border-purple-100">
        <div className="flex items-center gap-3">
          <CalendarCheck className="text-purple-600" size={24} />
          <div>
            <p className="font-semibold text-gray-900">Уроков в день</p>
            <p className="text-xs text-gray-500">Защита от выгорания и залог стабильного прогресса</p>
          </div>
        </div>
        <span className="text-3xl font-bold text-purple-600">{value}</span>
      </div>
      
      <input
        type="range"
        min={min}
        max={max}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
      />
      
      <div className="flex justify-between text-xs text-gray-500 px-1">
        <span>{min} (Для начинающих)</span>
        <span>3 (Оптимально)</span>
        <span>{max} (Максимум)</span>
      </div>
    </div>
  );
}