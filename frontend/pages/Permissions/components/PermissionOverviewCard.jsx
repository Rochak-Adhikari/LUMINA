// frontend/pages/Permissions/components/PermissionOverviewCard.jsx — summary stat tile
import React from 'react';
import { GlassCard } from '../../../components/ui';
import { cn } from '../../../utils/cn';

const TONE = {
  primary: 'text-primary',
  green:   'text-green-400',
  orange:  'text-orange-400',
  neutral: 'text-on-surface',
};

export function PermissionOverviewCard({ label, value, tone = 'neutral', icon: Icon }) {
  return (
    <GlassCard hover className="p-4 flex items-center gap-4">
      {Icon && (
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-primary shrink-0">
          <Icon size={18} />
        </div>
      )}
      <div className="min-w-0">
        <div className="text-[10px] uppercase tracking-widest text-on-surface-variant/60">{label}</div>
        <div className={cn('mt-0.5 font-mono text-2xl font-semibold', TONE[tone])}>{value}</div>
      </div>
    </GlassCard>
  );
}

export default PermissionOverviewCard;
