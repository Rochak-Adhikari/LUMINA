// frontend/components/browser/BrowserTabs.jsx — tab strip
import React from 'react';
import { BrowserTab } from './BrowserTab';

export function BrowserTabs({ tabs, activeTabId, onSelect, onClose }) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide border-b border-white/5 bg-black/60 px-4 py-1.5">
      {tabs.map((tab) => (
        <BrowserTab
          key={tab.id}
          tab={tab}
          active={tab.id === activeTabId}
          closable={tabs.length > 1}
          onSelect={onSelect}
          onClose={onClose}
        />
      ))}
    </div>
  );
}

export default BrowserTabs;
