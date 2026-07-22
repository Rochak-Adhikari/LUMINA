// frontend/components/ui/Button.jsx — primary/ghost/danger button
import React from 'react';
import { cn } from '../../utils/cn';

const VARIANTS = {
  primary: 'border-primary-container/40 bg-primary-container/20 text-primary hover:bg-primary-container/30 shadow-[0_0_8px_rgba(6,182,212,0.15)]',
  ghost: 'border-transparent bg-white/5 text-on-surface-variant hover:bg-white/10 hover:text-white',
  outline: 'border-white/10 bg-transparent text-on-surface-variant hover:border-primary-container/40 hover:text-primary',
  danger: 'border-red-500/40 bg-red-500/10 text-red-300 hover:bg-red-500/20',
};
const SIZES = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-sm',
};

export function Button({ variant = 'primary', size = 'md', className, icon: Icon, children, ...rest }) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-xl border font-medium transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed',
        VARIANTS[variant], SIZES[size], className
      )}
      {...rest}
    >
      {Icon && <Icon size={size === 'sm' ? 14 : 16} />}
      {children}
    </button>
  );
}

export default Button;
