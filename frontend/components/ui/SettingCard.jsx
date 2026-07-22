// frontend/components/ui/SettingCard.jsx — glass setting row (VS Code / Win11 style)
import React from 'react';
import { GlassCard } from './GlassCard';
import { cn } from '../../utils/cn';

/**
 * A single labeled setting row inside a glass card: title + description on the
 * left, control slot on the right. The reusable atom of the Settings page.
 */
export function SettingCard({ title, description, control, className }) {
  return (
    <GlassCard hover className={cn('flex items-center justify-between gap-4 p-4', className)}>
      <div className="min-w-0">
        <div className="text-sm text-on-surface">{title}</div>
        {description && <div className="mt-0.5 text-[11px] text-on-surface-variant/70">{description}</div>}
      </div>
      <div className="shrink-0">{control}</div>
    </GlassCard>
  );
}

/** Groups several SettingCards under a category heading. */
export function SettingGroup({ title, children, className }) {
  return (
    <section className={cn('flex flex-col gap-3', className)}>
      {title && (
        <h3 className="text-xs font-bold uppercase tracking-widest text-primary/70 mb-1">{title}</h3>
      )}
      {children}
    </section>
  );
}

export default SettingCard;
