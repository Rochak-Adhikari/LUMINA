// frontend/components/browser/BrowserToolbar.jsx — nav controls + address + actions
import React from 'react';
import { ChevronLeft, ChevronRight, RotateCw, Plus, Download, Terminal } from 'lucide-react';
import { AddressBar } from './AddressBar';
import { cn } from '../../utils/cn';

const IconBtn = ({ onClick, title, active, children }) => (
  <button
    onClick={onClick}
    title={title}
    className={cn('rounded-lg p-1.5 transition-colors hover:bg-white/5',
      active ? 'bg-primary-container/20 text-primary' : 'text-on-surface-variant hover:text-primary')}
  >
    {children}
  </button>
);

export function BrowserToolbar({
  url, onUrlChange, onNavigate, bookmarked, onToggleBookmark,
  onBack, onForward, onReload, onNewTab, onToggleDownloads, onToggleDevtools, downloadsOpen,
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-1.5">
        <IconBtn onClick={onBack} title="Back"><ChevronLeft size={16} /></IconBtn>
        <IconBtn onClick={onForward} title="Forward"><ChevronRight size={16} /></IconBtn>
        <IconBtn onClick={onReload} title="Reload"><RotateCw size={14} /></IconBtn>
      </div>
      <AddressBar value={url} onChange={onUrlChange} onSubmit={onNavigate} bookmarked={bookmarked} onToggleBookmark={onToggleBookmark} />
      <div className="flex items-center gap-1.5">
        <IconBtn onClick={onToggleDownloads} title="Downloads" active={downloadsOpen}><Download size={15} /></IconBtn>
        <IconBtn onClick={onToggleDevtools} title="Developer tools"><Terminal size={15} /></IconBtn>
        <button onClick={onNewTab} className="rounded-lg border border-primary-container/30 bg-primary-container/20 p-1.5 text-primary transition-transform hover:scale-105" title="New tab">
          <Plus size={15} />
        </button>
      </div>
    </div>
  );
}

export default BrowserToolbar;
