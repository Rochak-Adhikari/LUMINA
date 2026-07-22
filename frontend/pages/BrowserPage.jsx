// frontend/pages/BrowserPage.jsx — presentation only. State/IPC via useBrowser.
import React, { useRef, useState } from 'react';
import { Globe } from 'lucide-react';
import { PageHeader, GlassCard } from '../components/ui';
import {
  BrowserToolbar, BrowserTabs, BrowserBookmarks, BrowserDownloads, BrowserStatus,
} from '../components/browser';
import { useBrowser } from '../hooks/useBrowser';

const DEFAULT_BOOKMARKS = [
  { title: 'Google', url: 'https://www.google.com' },
  { title: 'GitHub', url: 'https://github.com' },
  { title: 'YouTube', url: 'https://youtube.com' },
];

export default function BrowserPage() {
  const viewRef = useRef(null);
  const b = useBrowser(viewRef);
  const [bookmarks, setBookmarks] = useState(DEFAULT_BOOKMARKS);
  const [downloadsOpen, setDownloadsOpen] = useState(false);

  const isBookmarked = !!(b.activeTab && bookmarks.some((bm) => bm.url === b.activeTab.url));
  const toggleBookmark = () => {
    if (!b.activeTab) return;
    setBookmarks((prev) => (prev.some((bm) => bm.url === b.activeTab.url)
      ? prev.filter((bm) => bm.url !== b.activeTab.url)
      : [...prev, { title: b.activeTab.title, url: b.activeTab.url }]));
  };

  return (
    <div className="flex h-[calc(100vh-9rem)] flex-col">
      <PageHeader title="Browser" subtitle="Embedded browser workspace" icon={Globe} />

      <GlassCard className="relative flex min-h-0 flex-1 flex-col overflow-hidden p-0">
        {/* Toolbar + bookmarks */}
        <div className="shrink-0 space-y-1.5 border-b border-white/5 bg-black/40 px-4 py-2.5">
          <BrowserToolbar
            url={b.url}
            onUrlChange={b.setInputUrl}
            onNavigate={b.navigate}
            bookmarked={isBookmarked}
            onToggleBookmark={toggleBookmark}
            onBack={b.back}
            onForward={b.forward}
            onReload={b.reload}
            onNewTab={() => b.createTab()}
            onToggleDownloads={() => setDownloadsOpen((v) => !v)}
            onToggleDevtools={b.toggleDevtools}
            downloadsOpen={downloadsOpen}
          />
          <BrowserBookmarks bookmarks={bookmarks} onOpen={(url) => { b.setInputUrl(url); b.navigate(url); }} />
        </div>

        {/* Tabs */}
        <BrowserTabs tabs={b.tabs} activeTabId={b.activeTabId} onSelect={b.switchTab} onClose={b.closeTab} />

        {/* BrowserView placeholder — the native view is positioned over this element */}
        <div ref={viewRef} className="relative min-h-0 flex-1 bg-[#030405]">
          <BrowserStatus isElectron={b.isElectron} loading={b.loading} />
        </div>

        <BrowserDownloads downloads={b.downloads} open={downloadsOpen} onClose={() => setDownloadsOpen(false)} />
      </GlassCard>
    </div>
  );
}
