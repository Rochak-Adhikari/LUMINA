// frontend/components/browser/BrowserTab.jsx — single tab pill
import React from 'react';
import { X } from 'lucide-react';
import { cn } from '../../utils/cn';

export function BrowserTab({ tab, active, closable, onSelect, onClose }) {
  return (
    <div
      onClick={() => onSelect(tab.id)}
      className={cn(
        'group flex max-w-[160px] cursor-pointer select-none items-center gap-2.5 truncate rounded-xl border px-4 py-2 font-mono text-xs transition-all duration-300',
        active
          ? 'border-primary-container/40 bg-primary-container/10 font-semibold text-primary shadow-[0_0_12px_rgba(0,212,255,0.15)]'
          : 'border-transparent bg-white/5 text-on-surface-variant hover:bg-white/10 hover:text-white'
      )}
    >
      {tab.favicon ? (
        <img src={tab.favicon} alt="" className="h-3.5 w-3.5 object-contain" />
      ) : (
        <div className={cn('h-2 w-2 rounded-full', tab.loading ? 'animate-pulse bg-primary' : 'bg-on-surface-variant/30')} />
      )}
      <span className="flex-1 truncate text-[11px]">{tab.title}</span>
      {closable && (
        <button
          onClick={(e) => { e.stopPropagation(); onClose(tab.id); }}
          className="ml-1.5 rounded-full p-0.5 text-on-surface-variant opacity-0 transition-opacity hover:bg-white/20 group-hover:opacity-100"
        >
          <X size={10} />
        </button>
      )}
    </div>
  );
}

export default BrowserTab;
