// frontend/components/browser/BrowserStatus.jsx — loading / preview-mode banner
import React from 'react';
import { GlassCard } from '../ui';

export function BrowserStatus({ isElectron, loading }) {
  if (!isElectron) {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center text-center">
        <div className="font-sora text-lg font-semibold text-primary">Preview Mode</div>
        <p className="mt-1 text-sm text-on-surface-variant/60">
          Browser features are unavailable outside the Lumina desktop app.
        </p>
      </div>
    );
  }
  if (loading) {
    return (
      <div className="pointer-events-none absolute left-0 top-0 h-0.5 w-full overflow-hidden">
        <div className="h-full w-1/3 animate-[loading_1s_ease-in-out_infinite] bg-primary" />
      </div>
    );
  }
  return null;
}

export default BrowserStatus;
