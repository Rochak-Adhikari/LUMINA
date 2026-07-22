// frontend/components/browser/BrowserBookmarks.jsx — quick bookmarks bar
import React from 'react';
import { Bookmark } from 'lucide-react';

export function BrowserBookmarks({ bookmarks, onOpen }) {
  if (!bookmarks || bookmarks.length === 0) return null;
  return (
    <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide py-1">
      {bookmarks.map((b, i) => (
        <button
          key={`${b.url}-${i}`}
          onClick={() => onOpen(b.url)}
          className="flex items-center gap-1.5 whitespace-nowrap rounded-full border border-white/5 bg-white/5 px-3 py-1 font-mono text-[10px] text-on-surface-variant transition-all hover:border-primary-container/40 hover:text-primary"
        >
          <Bookmark size={8} className="fill-current text-primary" />
          <span>{b.title}</span>
        </button>
      ))}
    </div>
  );
}

export default BrowserBookmarks;
