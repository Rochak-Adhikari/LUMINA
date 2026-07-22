// frontend/layout/Sidebar.jsx — collapsible left nav: logo, current project,
// primary/utility nav, and a footer with profile + connection + Gemini status.
// Presentation only — all state comes from stores/hooks.
import React from 'react';
import { PanelLeftClose, PanelLeftOpen, User, GitBranch } from 'lucide-react';
import { ROUTES } from '../app/routes';
import { useNavStore } from '../stores/useNavStore';
import { useWorkspaceStore } from '../stores/useWorkspaceStore';
import { useConnectionStatus } from '../hooks/useConnectionStatus';
import { useVoiceStore } from '../stores/useVoiceStore';
import { cn } from '../utils/cn';

function NavItem({ route, active, collapsed, onClick }) {
  const Icon = route.icon;
  return (
    <button
      onClick={onClick}
      title={collapsed ? route.label : undefined}
      className={cn(
        'group flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-200 w-full',
        active
          ? 'bg-primary-container/10 border border-primary-container/40 text-primary shadow-[0_0_12px_rgba(0,212,255,0.12)]'
          : 'border border-transparent text-on-surface-variant hover:bg-white/5 hover:text-white'
      )}
    >
      <Icon size={18} className="shrink-0" />
      {!collapsed && <span className="text-sm font-medium truncate">{route.label}</span>}
    </button>
  );
}

const STATUS_DOT = {
  connected: 'bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.5)]',
  connecting: 'bg-yellow-400 animate-pulse',
  disconnected: 'bg-red-400',
};

export function Sidebar() {
  const { activePage, sidebarCollapsed, toggleSidebar, navigateTo } = useNavStore();
  const project = useWorkspaceStore((s) => s.project);
  const branch = useWorkspaceStore((s) => s.branch);
  const { status: connStatus } = useConnectionStatus();
  const modelStatus = useVoiceStore((s) => s.modelStatus);

  const main = ROUTES.filter((r) => r.group === 'main' && !r.hidden);
  const util = ROUTES.filter((r) => r.group === 'util' && !r.hidden);

  const geminiDot = STATUS_DOT[modelStatus === 'connected' ? 'connected' : modelStatus === 'connecting' ? 'connecting' : 'disconnected'];
  const connDot = STATUS_DOT[connStatus] || STATUS_DOT.disconnected;

  return (
    <aside
      className={cn(
        'flex flex-col h-full w-full border-r border-white/5 bg-surface-container-lowest/60 backdrop-blur-2xl',
        sidebarCollapsed && 'w-[68px]'
      )}
    >
      {/* Brand + collapse toggle */}
      <div className="flex items-center justify-between px-4 h-16 shrink-0">
        {!sidebarCollapsed && (
          <span className="font-sora text-xl font-semibold tracking-tighter text-primary">Lumina</span>
        )}
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-lg text-on-surface-variant hover:text-primary hover:bg-white/5 transition-colors"
        >
          {sidebarCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      {/* Current Project */}
      {!sidebarCollapsed && (
        <div className="mx-3 mb-3 rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2.5">
          <div className="text-[9px] uppercase tracking-widest text-on-surface-variant/50">Current Project</div>
          <div className="mt-0.5 truncate text-sm font-semibold text-on-surface">{project}</div>
          <div className="mt-0.5 flex items-center gap-1 text-[10px] text-on-surface-variant/60">
            <GitBranch size={10} />
            <span className="truncate">{branch}</span>
          </div>
        </div>
      )}

      {/* Primary nav */}
      <nav className="flex-1 flex flex-col gap-1 px-3 overflow-y-auto scrollbar-hide">
        {main.map((r) => (
          <NavItem
            key={r.id}
            route={r}
            active={activePage === r.id}
            collapsed={sidebarCollapsed}
            onClick={() => navigateTo(r.id, r.deepTab ?? null)}
          />
        ))}
      </nav>

      {/* Utility nav */}
      <div className="flex flex-col gap-1 px-3 pb-3 border-t border-white/5 pt-3">
        {util.map((r) => (
          <NavItem
            key={r.id}
            route={r}
            active={activePage === r.id}
            collapsed={sidebarCollapsed}
            onClick={() => navigateTo(r.id, r.deepTab ?? null)}
          />
        ))}
      </div>

      {/* Footer: profile + connection + Gemini status */}
      <div className="flex flex-col gap-2 border-t border-white/5 px-3 py-3">
        <div className={cn('flex items-center gap-2.5', sidebarCollapsed && 'justify-center')}>
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-on-surface-variant">
            <User size={14} />
          </div>
          {!sidebarCollapsed && <span className="truncate text-xs text-on-surface-variant">Local User</span>}
        </div>
        {!sidebarCollapsed ? (
          <div className="flex flex-col gap-1 font-mono text-[10px]">
            <div className="flex items-center gap-1.5">
              <span className={cn('h-1.5 w-1.5 rounded-full', connDot)} />
              <span className="text-on-surface-variant/60">Backend: {connStatus}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={cn('h-1.5 w-1.5 rounded-full', geminiDot)} />
              <span className="text-on-surface-variant/60">Gemini: {modelStatus}</span>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1.5">
            <span className={cn('h-1.5 w-1.5 rounded-full', connDot)} title={`Backend: ${connStatus}`} />
            <span className={cn('h-1.5 w-1.5 rounded-full', geminiDot)} title={`Gemini: ${modelStatus}`} />
          </div>
        )}
      </div>
    </aside>
  );
}

export default Sidebar;
