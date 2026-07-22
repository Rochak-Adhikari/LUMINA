// frontend/components/workspace/Field.jsx — token-styled form primitives
import React from 'react';
import { cn } from '../../utils/cn';

const base =
  'w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-on-surface ' +
  'placeholder-on-surface-variant/40 focus:outline-none focus:border-primary-container/50 transition-all';

export function TextField({ className, ...rest }) {
  return <input type="text" className={cn(base, className)} {...rest} />;
}

export function DateTimeField({ className, ...rest }) {
  return <input type="datetime-local" className={cn(base, className)} {...rest} />;
}

export function TextArea({ className, rows = 3, ...rest }) {
  return <textarea rows={rows} className={cn(base, 'resize-none', className)} {...rest} />;
}

export function SelectField({ options = [], className, ...rest }) {
  return (
    <select className={cn(base, className)} {...rest}>
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}

export function FieldLabel({ children }) {
  return <span className="mb-1 block text-[10px] uppercase tracking-widest text-on-surface-variant/50">{children}</span>;
}
