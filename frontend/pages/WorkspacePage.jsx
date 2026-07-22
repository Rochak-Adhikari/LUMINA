// frontend/pages/WorkspacePage.jsx — tabbed shell over the three workspace views
import React, { useEffect, useState } from 'react';
import { Swords, CalendarDays, Archive } from 'lucide-react';
import { QuestsView } from './Workspace/QuestsView';
import { EventsView } from './Workspace/EventsView';
import { ArchiveView } from './Workspace/ArchiveView';
import { useNavStore } from '../stores/useNavStore';
import { cn } from '../utils/cn';

const TABS = [
  { id: 'quests', label: 'Quests', icon: Swords, Component: QuestsView },
  { id: 'events', label: 'Events', icon: CalendarDays, Component: EventsView },
  { id: 'archive', label: 'Archive', icon: Archive, Component: ArchiveView },
];

export default function WorkspacePage() {
  const [tab, setTab] = useState('quests');
  // Voice navigation can deep-link into a sub-tab via the nav store.
  const workspaceTab = useNavStore((s) => s.workspaceTab);
  useEffect(() => {
    if (workspaceTab && TABS.some((t) => t.id === workspaceTab)) setTab(workspaceTab);
  }, [workspaceTab]);
  const Active = TABS.find((t) => t.id === tab)?.Component || QuestsView;

  return (
    <div>
      {/* Sub-navigation */}
      <div className="mb-6 flex gap-2 border-b border-white/5 pb-3">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={cn('inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs transition-all duration-200',
              tab === id ? 'bg-primary-container/15 text-primary' : 'text-on-surface-variant hover:text-primary')}>
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>
      <Active />
    </div>
  );
}
