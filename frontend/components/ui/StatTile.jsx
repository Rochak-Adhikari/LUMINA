// frontend/components/ui/StatTile.jsx — compact labelled metric tile
import React from 'react';
import { GlassCard } from './GlassCard';
import { cn } from '../../utils/cn';

/**
 * Small key/value tile for dashboards (Diagnostics, future status views).
 * Extracted from the inline Diagnostics grid so any page can reuse it.
 */
export function StatTile({ label, value, icon: Icon, mono = true, className }) {
  return (
    <GlassCard className={cn('p-4', className)} hover>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-on-surface-variant/60">
        {Icon && <Icon size={12} className="text-primary/50" />}
        {label}
      </div>
      <div className={cn('mt-1 text-lg text-primary truncate', mono && 'font-mono')} title={String(value)}>
        {value}
      </div>
    </GlassCard>
  );
}

export default StatTile;
