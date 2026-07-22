// frontend/components/settings/SettingsError.jsx — friendly load-failure panel
import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { GlassCard, Button } from '../ui';
import { useSettingsStore } from '../../stores/useSettingsStore';

export function SettingsError({ message }) {
  const reload = useSettingsStore((s) => s.reload);
  const reset = useSettingsStore((s) => s.reset);
  return (
    <GlassCard glow className="p-6 border-red-500/20">
      <div className="flex items-center gap-3 text-red-300">
        <AlertTriangle size={20} />
        <span className="font-sora text-lg font-semibold">Couldn’t load settings</span>
      </div>
      <p className="mt-2 text-sm text-on-surface-variant/80">
        {message || 'The configuration could not be read.'} Your changes are safe —
        you can retry or restore defaults.
      </p>
      <div className="mt-5 flex gap-3">
        <Button variant="primary" onClick={reload}>Retry</Button>
        <Button variant="outline" onClick={reset}>Restore Defaults</Button>
      </div>
    </GlassCard>
  );
}

export default SettingsError;
