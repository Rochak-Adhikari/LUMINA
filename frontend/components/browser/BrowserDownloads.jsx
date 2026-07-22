// frontend/components/browser/BrowserDownloads.jsx — downloads drawer
import React from 'react';
import { GlassCard } from '../ui';

export function BrowserDownloads({ downloads, open, onClose }) {
  if (!open || !downloads || downloads.length === 0) return null;
  return (
    <GlassCard className="absolute bottom-4 right-4 z-50 flex max-h-60 w-72 flex-col gap-3 overflow-y-auto scrollbar-hide p-4 shadow-2xl animate-fade-in">
      <div className="flex shrink-0 items-center justify-between border-b border-white/5 pb-2">
        <span className="font-mono text-xs font-bold tracking-widest text-primary">DOWNLOADS</span>
        <button onClick={onClose} className="text-xs text-on-surface-variant hover:text-white">✕</button>
      </div>
      <div className="flex flex-col gap-3">
        {downloads.map((d) => (
          <div key={d.id} className="flex flex-col gap-1.5 rounded-lg border border-white/5 bg-white/5 p-2 text-[10px]">
            <div className="flex justify-between truncate font-mono font-medium text-white">
              <span className="truncate">{d.name}</span>
              <span>{d.progress}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
              <div className="h-full rounded-full bg-primary transition-all duration-300" style={{ width: `${d.progress}%` }} />
            </div>
            <div className="flex justify-between font-mono text-[9px] text-on-surface-variant opacity-60">
              <span>{d.state}</span>
              {d.totalBytes ? <span>{Math.round((d.totalBytes / 1024 / 1024) * 10) / 10} MB</span> : null}
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

export default BrowserDownloads;
