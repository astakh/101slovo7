import { BookOpen } from 'lucide-react';

interface WordsPerLessonSelectorProps {
  value: number;
  onChange: (val: number) => void;
  min?: number;
  max?: number;
}

export default function WordsPerLessonSelector({ 
  value, 
  onChange, 
  min = 1, 
  max = 10 
}: WordsPerLessonSelectorProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between p-4 bg-indigo-50 rounded-xl border border-indigo-100">
        <div className="flex items-center gap-3">
          <BookOpen className="text-indigo-600" size={24} />
          <div>
            <p className="font-semibold text-gray-900">Слов в одном уроке</p>
            <p className="text-xs text-gray-500">Рекомендуем 5-7 для комфортного запоминания</p>
          </div>
        </div>
        <span className="text-3xl font-bold text-indigo-600">{value}</span>
      </div>
      
      <input
        type="range"
        min={min}
        max={max}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
      />
      
      <div className="flex justify-between text-xs text-gray-500 px-1">
        <span>{min} (Лайт)</span>
        <span>5 (Стандарт)</span>
        <span>{max} (Хардкор)</span>
      </div>
    </div>
  );
}