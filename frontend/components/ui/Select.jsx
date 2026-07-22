// frontend/components/ui/Select.jsx — styled native select
import React from 'react';
import { cn } from '../../utils/cn';

export function Select({ value, onChange, options = [], disabled = false, className }) {
  return (
    <select
      value={value}
      disabled={disabled}
      onChange={(e) => onChange && onChange(e.target.value)}
      className={cn(
        'w-full rounded-lg border border-white/10 bg-gray-900/80 px-3 py-2 text-xs text-primary',
        'focus:outline-none focus:border-primary-container/50 transition-colors disabled:opacity-40',
        className
      )}
    >
      {options.map((o) => (
        <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>
      ))}
    </select>
  );
}

export default Select;
