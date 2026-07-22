// frontend/components/ui/Toggle.jsx — binary on/off pill (controlled)
import React from 'react';
import { cn } from '../../utils/cn';

export function Toggle({ checked = false, onChange, disabled = false, className }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => !disabled && onChange && onChange(!checked)}
      className={cn(
        'relative w-9 h-5 rounded-full transition-colors duration-200 shrink-0',
        disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer',
        checked ? 'bg-primary-container/80' : 'bg-gray-700',
        className
      )}
    >
      <span
        className={cn(
          'absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200',
          checked ? 'translate-x-4' : 'translate-x-0'
        )}
      />
    </button>
  );
}

export default Toggle;
