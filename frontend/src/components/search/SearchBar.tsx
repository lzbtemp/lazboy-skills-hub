import { useEffect, useState } from 'react';
import { Search, X } from 'lucide-react';

interface Props {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export default function SearchBar({ value, onChange, placeholder = 'Search skills...' }: Props) {
  const [local, setLocal] = useState(value);
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    setLocal(value);
  }, [value]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (local !== value) onChange(local);
    }, 300);
    return () => clearTimeout(timer);
  }, [local, value, onChange]);

  return (
    <div className={`relative transition-all duration-300 ${focused ? 'scale-[1.01]' : ''}`}>
      <Search className={`absolute left-4 top-1/2 -translate-y-1/2 w-4.5 h-4.5 transition-colors duration-200 ${focused ? 'text-[#1B3A6B]/50' : 'text-[#2C2C2C]/25'}`} />
      <input
        type="text"
        value={local}
        onChange={(e) => setLocal(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        className="w-full pl-12 pr-10 py-3.5 bg-white border border-gray-100 rounded-2xl text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-[#1B3A6B]/15 focus:border-[#1B3A6B]/20 focus:shadow-lg focus:shadow-[#1B3A6B]/5 transition-all duration-300"
      />
      {local && (
        <button
          onClick={() => { setLocal(''); onChange(''); }}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 rounded-full text-[#2C2C2C]/25 hover:text-[#2C2C2C]/60 hover:bg-[#1B3A6B]/5 transition-all"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}
