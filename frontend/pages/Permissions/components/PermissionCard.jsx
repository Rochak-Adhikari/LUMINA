// frontend/pages/Permissions/components/PermissionCard.jsx
import React from 'react';
import { GlassCard } from '../../../components/ui';
import { PermissionBadge } from './PermissionBadge';
import { PermissionToggle } from './PermissionToggle';
import { cn } from '../../../utils/cn';

/**
 * One permission row: icon + name + description on the left, risk badge +
 * status + toggle on the right. Fully data-driven from a schema entry.
 */
export function PermissionCard({ permission, enabled, onToggle }) {
  const Icon = permission.icon;
  const isDisabled = !!permission.disabled;
  return (
    <GlassCard hover glow className={cn('flex items-start gap-4 p-4', isDisabled && 'opacity-60')}>
      {/* Icon */}
      <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-primary">
        {Icon && <Icon size={16} />}
      </div>

      {/* Name + description */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-on-surface">{permission.title}</span>
          <PermissionBadge risk={permission.risk} />
        </div>
        <p className="mt-1 text-[11px] leading-relaxed text-on-surface-variant/70">
          {permission.description}
        </p>
      </div>

      {/* Status + toggle */}
      <div className="flex flex-col items-end gap-2 shrink-0">
        <span className={cn(
          'text-[10px] font-mono uppercase tracking-wider',
          isDisabled ? 'text-on-surface-variant/40'
            : enabled ? 'text-green-400' : 'text-on-surface-variant/50'
        )}>
          {isDisabled ? 'Locked' : enabled ? 'Enabled' : 'Disabled'}
        </span>
        <PermissionToggle enabled={enabled} onChange={onToggle} disabled={isDisabled} />
      </div>
    </GlassCard>
  );
}

export default PermissionCard;
