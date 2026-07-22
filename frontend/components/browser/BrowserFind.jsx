// frontend/components/browser/BrowserFind.jsx — in-page find bar (presentation only)
import React, { useState } from 'react';
import { X, ArrowUp, ArrowDown } from 'lucide-react';
import { GlassCard } from '../ui';

export function BrowserFind({ open, onFind, onClose }) {
  const [query, setQuery] = useState('');
  if (!open) return null;
  return (
    <GlassCard className="absolute right-4 top-4 z-50 flex items-center gap-2 p-2 shadow-2xl">
      <input
        autoFocus
        type="text"
        value={query}
        onChange={(e) => { setQuery(e.target.value); onFind?.(e.target.value); }}
        onKeyDown={(e) => { if (e.key === 'Enter') onFind?.(query); if (e.key === 'Escape') onClose(); }}
        placeholder="Find in page…"
        className="w-40 bg-transparent px-2 text-xs text-white outline-none placeholder-on-surface-variant/40 focus:ring-0"
      />
      <button onClick={() => onFind?.(query)} className="rounded p-1 text-on-surface-variant hover:text-primary"><ArrowUp size={13} /></button>
      <button onClick={() => onFind?.(query)} className="rounded p-1 text-on-surface-variant hover:text-primary"><ArrowDown size={13} /></button>
      <button onClick={onClose} className="rounded p-1 text-on-surface-variant hover:text-white"><X size={13} /></button>
    </GlassCard>
  );
}

export default BrowserFind;
