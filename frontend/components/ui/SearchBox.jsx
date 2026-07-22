// frontend/components/ui/SearchBox.jsx — global search input (top bar)
import React from 'react';
import { Search } from 'lucide-react';
import { cn } from '../../utils/cn';

export function SearchBox({ value, onChange, placeholder = 'Search Lumina…', className }) {
  return (
    <div className={cn(
      'flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5',
      'focus-within:border-primary-container/40 transition-colors', className
    )}>
      <Search size={14} className="text-on-surface-variant/60 shrink-0" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange && onChange(e.target.value)}
        placeholder={placeholder}
        className="flex-1 bg-transparent border-0 outline-none text-xs text-white placeholder-on-surface-variant/40 focus:ring-0"
      />
    </div>
  );
}

export default SearchBox;
