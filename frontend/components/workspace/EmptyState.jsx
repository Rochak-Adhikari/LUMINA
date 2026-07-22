// frontend/components/workspace/EmptyState.jsx — reusable empty placeholder
import React from 'react';

export function EmptyState({ icon: Icon, title, hint }) {
  return (
    <div className="text-center py-16">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-white/10">
        {Icon && <Icon size={20} className="text-on-surface-variant/50" />}
      </div>
      <p className="mb-1 text-sm text-on-surface-variant/70">{title}</p>
      {hint && <p className="text-xs text-on-surface-variant/40">{hint}</p>}
    </div>
  );
}

export default EmptyState;
