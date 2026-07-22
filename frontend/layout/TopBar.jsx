// frontend/layout/TopBar.jsx — top navigation bar: workspace info + global search
import React from 'react';
import { ChevronRight } from 'lucide-react';
import { SearchBox } from '../components/ui/SearchBox';
import { useNavStore } from '../stores/useNavStore';
import { useConnectionStatus } from '../hooks/useConnectionStatus';
import { getRoute } from '../app/routes';

const STATUS_UI = {
  connected:    { dot: 'bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.5)]', label: 'Connected' },
  connecting:   { dot: 'bg-yellow-400 animate-pulse', label: 'Connecting' },
  disconnected: { dot: 'bg-red-400', label: 'Disconnected' },
};

export function TopBar() {
  const { activePage, search, setSearch } = useNavStore();
  const { status } = useConnectionStatus();
  const route = getRoute(activePage);
  const conn = STATUS_UI[status] || STATUS_UI.connecting;

  return (
    <header className="flex items-center justify-between gap-6 h-16 shrink-0 px-6 border-b border-white/5 bg-transparent">
      {/* Workspace breadcrumb */}
      <div className="flex items-center gap-2 text-xs font-mono">
        <span className="text-primary/60 uppercase tracking-widest">Workspace</span>
        <ChevronRight size={12} className="text-on-surface-variant/40" />
        <span className="text-on-surface capitalize">{route.label}</span>
      </div>

      {/* Global search */}
      <div className="flex-1 max-w-md">
        <SearchBox value={search} onChange={setSearch} placeholder="Search Lumina — pages, settings, skills…" />
      </div>

      {/* Live backend connection status */}
      <div className="flex items-center gap-2 font-mono-ui text-xs">
        <span className={`w-2 h-2 rounded-full ${conn.dot}`} />
        <span className="text-on-surface-variant/70">{conn.label}</span>
      </div>
    </header>
  );
}

export default TopBar;
