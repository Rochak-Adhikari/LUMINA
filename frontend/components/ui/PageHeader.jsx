// frontend/components/ui/PageHeader.jsx — consistent page title block
import React from 'react';
import { cn } from '../../utils/cn';

export function PageHeader({ title, subtitle, icon: Icon, actions, className }) {
  return (
    <header className={cn('flex items-center justify-between mb-6', className)}>
      <div className="flex items-center gap-3">
        {Icon && (
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-primary-container/30 bg-primary-container/10 text-primary">
            <Icon size={18} />
          </div>
        )}
        <div>
          <h1 className="font-sora text-xl font-semibold tracking-tight text-on-surface">{title}</h1>
          {subtitle && <p className="text-xs text-on-surface-variant/70">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}

export default PageHeader;
