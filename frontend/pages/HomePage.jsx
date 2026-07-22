// frontend/pages/HomePage.jsx — command center dashboard. No right chat panel
// (AppShell hides it for this route). Presentation only; state via hooks.
import React, { useEffect, useState } from 'react';
import {
  Mic, Keyboard, Paperclip, Globe, Code2, FolderOpen, StickyNote, Music, Settings as SettingsIcon,
  GitBranch, Wifi, Brain, Cpu, Send, Clock,
} from 'lucide-react';
import { GlassCard, Button } from '../components/ui';
import { useVoice } from '../hooks/useVoice';
import { useChat } from '../hooks/useChat';
import { useChatHistory } from '../hooks/useChatHistory';
import { useMemory } from '../hooks/useMemory';
import { useConnectionStatus } from '../hooks/useConnectionStatus';
import { useWorkspaceStore } from '../stores/useWorkspaceStore';
import { useNavStore } from '../stores/useNavStore';
import { cn } from '../utils/cn';

const QUICK_ACTIONS = [
  { icon: Globe, label: 'Open Browser', page: 'browser' },
  { icon: Code2, label: 'Start Coding', page: 'developer' },
  { icon: FolderOpen, label: 'Open Project', page: 'workspace' },
  { icon: StickyNote, label: 'New Note', page: 'workspace', tab: 'archive' },
  { icon: Music, label: 'Play Music', page: 'skills' },
  { icon: SettingsIcon, label: 'Settings', page: 'settings' },
];

function greeting(hour) {
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

export default function HomePage() {
  const [text, setText] = useState('');
  const [now, setNow] = useState(new Date());
  const v = useVoice();
  const { send } = useChat();
  const { conversations } = useChatHistory();
  const { stats } = useMemory();
  const { status, isConnected } = useConnectionStatus();
  const project = useWorkspaceStore((s) => s.project);
  const branch = useWorkspaceStore((s) => s.branch);
  const navigateTo = useNavStore((s) => s.navigateTo);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const submit = () => {
    const t = text.trim();
    if (!t) return;
    if (send(t) !== false) setText('');
  };

  const recent = conversations.slice(0, 5);

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-8 pb-10">
      {/* Hero */}
      <div className="flex flex-col items-center gap-2 pt-6 text-center">
        <h1 className="font-sora text-3xl font-semibold text-on-surface">{greeting(now.getHours())}, Scepter.</h1>
        <div className="flex items-center gap-3 text-xs text-on-surface-variant/60">
          <span className="flex items-center gap-1"><Clock size={12} />{now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
          <span>·</span>
          <span className="flex items-center gap-1"><GitBranch size={12} />{project}/{branch}</span>
          <span>·</span>
          <span className={cn('flex items-center gap-1', isConnected ? 'text-green-400' : 'text-red-400')}>
            <Wifi size={12} />{status}
          </span>
        </div>
      </div>

      {/* Command box */}
      <GlassCard glow className="p-5">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          placeholder="Ask Lumina anything…"
          className="w-full bg-transparent text-lg text-on-surface outline-none placeholder-on-surface-variant/40"
        />
        <div className="mt-4 flex items-center gap-2">
          <Button variant={v.connected && !v.muted ? 'primary' : 'outline'} size="sm" icon={Mic} onClick={v.togglePower}>Voice</Button>
          <Button variant="outline" size="sm" icon={Keyboard} onClick={() => document.activeElement?.blur()}>Type</Button>
          <Button variant="outline" size="sm" icon={Paperclip}>Attach</Button>
          <Button variant="ghost" size="sm" icon={Send} className="ml-auto" onClick={submit} disabled={!text.trim()}>Send</Button>
        </div>
      </GlassCard>

      {/* Quick actions */}
      <div>
        <h2 className="mb-3 text-xs font-bold uppercase tracking-widest text-on-surface-variant/50">Quick Actions</h2>
        <div className="grid grid-cols-3 gap-3">
          {QUICK_ACTIONS.map((a) => (
            <GlassCard key={a.label} hover className="cursor-pointer p-4" onClick={() => navigateTo(a.page, a.tab ?? null)}>
              <a.icon size={18} className="mb-2 text-primary" />
              <div className="text-sm text-on-surface">{a.label}</div>
            </GlassCard>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Current workspace */}
        <div>
          <h2 className="mb-3 text-xs font-bold uppercase tracking-widest text-on-surface-variant/50">Current Workspace</h2>
          <GlassCard className="p-4">
            <div className="text-sm text-on-surface">{project}</div>
            <div className="mt-1 flex items-center gap-1 text-xs text-on-surface-variant/60"><GitBranch size={11} />{branch}</div>
            <div className="mt-2 text-xs text-on-surface-variant/50">Status: Active</div>
          </GlassCard>
        </div>

        {/* AI status */}
        <div>
          <h2 className="mb-3 text-xs font-bold uppercase tracking-widest text-on-surface-variant/50">AI Status</h2>
          <GlassCard className="grid grid-cols-2 gap-3 p-4 text-xs">
            <div className="flex items-center gap-1.5"><Wifi size={12} className={isConnected ? 'text-green-400' : 'text-red-400'} />Connected: {isConnected ? 'Yes' : 'No'}</div>
            <div className="flex items-center gap-1.5"><Cpu size={12} className="text-primary" />Gemini: {v.modelStatus}</div>
            <div className="flex items-center gap-1.5"><Brain size={12} className="text-primary" />Memory: {stats ? 'Ready' : 'Loading'}</div>
            <div className="flex items-center gap-1.5"><Mic size={12} className={v.connected ? 'text-green-400' : 'text-on-surface-variant/40'} />Voice: {v.connected ? 'Live' : 'Idle'}</div>
          </GlassCard>
        </div>
      </div>

      {/* Recent conversations */}
      <div>
        <h2 className="mb-3 text-xs font-bold uppercase tracking-widest text-on-surface-variant/50">Recent Conversations</h2>
        {recent.length === 0 ? (
          <GlassCard className="p-4 text-center text-xs text-on-surface-variant/40">No conversations yet</GlassCard>
        ) : (
          <div className="flex flex-col gap-2">
            {recent.map((c) => (
              <GlassCard key={c.id} hover className="cursor-pointer p-3 text-sm text-on-surface-variant" onClick={() => navigateTo('chat')}>
                {c.title}
              </GlassCard>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
