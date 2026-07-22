// frontend/components/ui/Slider.jsx — range slider with value readout
import React from 'react';
import { cn } from '../../utils/cn';

export function Slider({ value, min = 0, max = 100, step = 1, suffix = '', onChange, disabled = false, className }) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <input
        type="range"
        min={min} max={max} step={step} value={value} disabled={disabled}
        onChange={(e) => onChange && onChange(Number(e.target.value))}
        className="flex-1 h-1 rounded-lg appearance-none cursor-pointer bg-gray-700 accent-primary-container disabled:opacity-40"
      />
      <span className="w-12 text-right font-mono text-[10px] text-primary/60">{value}{suffix}</span>
    </div>
  );
}

export default Slider;
