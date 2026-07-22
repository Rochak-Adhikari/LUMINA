// frontend/components/browser/AddressBar.jsx — URL input (presentation only)
import React from 'react';
import { Shield, Bookmark } from 'lucide-react';
import { cn } from '../../utils/cn';

export function AddressBar({ value, onChange, onSubmit, bookmarked, onToggleBookmark }) {
  return (
    <div className="flex flex-1 items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-1.5">
      <Shield size={12} className="text-primary/60" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && value.trim()) onSubmit(value); }}
        placeholder="Search or enter address"
        className="flex-1 select-all bg-transparent font-mono text-xs text-white outline-none placeholder-on-surface-variant/30 focus:ring-0"
      />
      <button
        onClick={onToggleBookmark}
        className={cn('rounded p-1 transition-colors hover:bg-white/5', bookmarked ? 'text-primary' : 'text-on-surface-variant')}
        title="Bookmark page"
      >
        <Bookmark size={14} className={bookmarked ? 'fill-current' : ''} />
      </button>
    </div>
  );
}

export default AddressBar;
