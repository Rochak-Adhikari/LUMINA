// frontend/pages/Permissions/components/PermissionCategory.jsx — left-rail item
import React from 'react';
import { cn } from '../../../utils/cn';

export function PermissionCategory({ category, active, onClick, count }) {
  const Icon = category.icon;
  const danger = !!category.danger;
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all duration-200 w-full',
        active
          ? danger
            ? 'bg-red-500/10 border border-red-500/40 text-red-300'
            : 'bg-primary-container/10 border border-primary-container/40 text-primary shadow-[0_0_12px_rgba(0,212,255,0.12)]'
          : 'border border-transparent text-on-surface-variant hover:bg-white/5 hover:text-white'
      )}
    >
      <Icon size={16} className={cn('shrink-0', danger && !active && 'text-red-400/70')} />
      <span className="flex-1 truncate text-left">{category.label}</span>
      {typeof count === 'number' && (
        <span className="text-[10px] font-mono text-on-surface-variant/50">{count}</span>
      )}
    </button>
  );
}

export default PermissionCategory;
