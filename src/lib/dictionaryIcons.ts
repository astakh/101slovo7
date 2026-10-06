/**
 * Маппинг эмодзи-иконок для словарей по коду (Вариант А).
 * Если код словаря не найден в маппинге, используется дефолтная иконка.
 */
const DICTIONARY_ICONS: Record<string, string> = {
  general: '📚',
  business: '💼',
  travel: '✈️',
  it: '💻',
  medical: '🏥',
  science: '🔬',
  art: '🎨',
  sports: '⚽',
  food: '🍕',
  legal: '⚖️',
  finance: '💰',
  education: '🎓',
};

const DEFAULT_ICON = '📖';

export function getDictionaryIcon(code: string): string {
  return DICTIONARY_ICONS[code] || DEFAULT_ICON;
}