export const TIMEZONES = [
  'Europe/Moscow', 
  'Europe/Kiev', 
  'Europe/Minsk',
  'Europe/Berlin', 
  'Europe/London', 
  'America/New_York',
  'Asia/Almaty', 
  'Asia/Tashkent',
];

interface TimezoneSelectorProps {
  value: string;
  onChange: (timezone: string) => void;
}

export default function TimezoneSelector({ value, onChange }: TimezoneSelectorProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none bg-white"
    >
      <option value="">Выберите часовой пояс</option>
      {TIMEZONES.map((tz) => (
        <option key={tz} value={tz}>
          {tz}
        </option>
      ))}
    </select>
  );
}