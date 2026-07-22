// frontend/components/settings/SaveStatus.jsx — global Saved / Saving / Unsaved pill
import React from 'react';
import { Check, Loader2, Circle } from 'lucide-react';
import { useSettingsStatus } from '../../hooks/useSetting';
import { cn } from '../../utils/cn';

export function SaveStatus({ className }) {
  const { dirty, saving, lastSaved } = useSettingsStatus();

  let icon, label, tone;
  if (saving) { icon = <Loader2 size={12} className="animate-spin" />; label = 'Saving…'; tone = 'text-primary'; }
  else if (dirty) { icon = <Circle size={8} className="fill-current" />; label = 'Unsaved changes'; tone = 'text-yellow-400'; }
  else if (lastSaved) { icon = <Check size={12} />; label = 'Saved'; tone = 'text-green-400'; }
  else { icon = <Circle size={8} />; label = 'Idle'; tone = 'text-on-surface-variant/50'; }

  return (
    <div className={cn('flex items-center gap-1.5 font-mono text-[11px]', tone, className)}>
      {icon}<span>{label}</span>
    </div>
  );
}

export default SaveStatus;
