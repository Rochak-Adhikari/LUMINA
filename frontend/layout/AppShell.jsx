// frontend/layout/AppShell.jsx — 3-column desktop layout:
//   LEFT  = Sidebar (resizable, collapsible)
//   CENTER= TopBar + routed page (Browser / Workspace / Memory / Settings / …)
//   RIGHT = ChatPanel (always visible)
// Columns are resizable via dependency-free dividers; widths persist in the
// settings store. The center absorbs the remaining space (min 400px enforced).
import React, { useCallback, useEffect, useRef } from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { ChatPanel } from './ChatPanel';
import { ResizeDivider } from '../components/layout/ResizeDivider';
import { useNavStore } from '../stores/useNavStore';
import { useSettingsStore } from '../stores/useSettingsStore';
import { useConnectionStatus } from '../hooks/useConnectionStatus';
import { useVoiceNavigation } from '../hooks/useVoiceNavigation';
import { useProject } from '../hooks/useProject';
import { useSetting } from '../hooks/useSetting';
import { ConfirmationOverlay } from '../components/confirmation';
import { AlarmOverlay } from '../components/alarm';
import { getRoute } from '../app/routes';

const MIN_SIDEBAR = 220, MAX_SIDEBAR = 420;
const MIN_CENTER = 400;
const MIN_CHAT = 360, MAX_CHAT = 720;
const COLLAPSED_SIDEBAR = 68;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

export function AppShell() {
  const activePage = useNavStore((s) => s.activePage);
  const sidebarCollapsed = useNavStore((s) => s.sidebarCollapsed);
  const loadSettings = useSettingsStore((s) => s.load);
  const reloadSettings = useSettingsStore((s) => s.reload);
  const dirty = useSettingsStore((s) => s.dirty);
  const { isConnected } = useConnectionStatus();
  const route = getRoute(activePage);
  const Page = route.component;
  const showChatPanel = !route.noChatPanel;

  const [sidebarW, setSidebarW] = useSetting('layout_sidebar_w', 220);
  const [chatW, setChatW] = useSetting('layout_chat_w', 380);
  const containerRef = useRef(null);

  // Session subscriptions that must always be mounted.
  useVoiceNavigation();     // backend 'navigate_panel' → nav store
  useProject();             // backend 'project_update' + 'workspace_open'

  useEffect(() => { loadSettings(); }, [loadSettings]);
  useEffect(() => {
    if (isConnected && !dirty) reloadSettings();
  }, [isConnected]); // eslint-disable-line react-hooks/exhaustive-deps

  const totalWidth = () => containerRef.current?.getBoundingClientRect().width || window.innerWidth;
  const effectiveSidebar = sidebarCollapsed ? COLLAPSED_SIDEBAR : sidebarW;

  // Divider between Sidebar | Center — grows/shrinks the sidebar.
  const resizeSidebar = useCallback((dx) => {
    const maxByCenter = totalWidth() - chatW - MIN_CENTER; // keep center >= min
    setSidebarW((w) => clamp((w || 220) + dx, MIN_SIDEBAR, Math.min(MAX_SIDEBAR, maxByCenter)));
  }, [chatW, setSidebarW]);

  // Divider between Center | Chat — dragging left grows chat (invert dx).
  const resizeChat = useCallback((dx) => {
    const maxByCenter = totalWidth() - effectiveSidebar - MIN_CENTER;
    setChatW((w) => clamp((w || 380) - dx, MIN_CHAT, Math.min(MAX_CHAT, maxByCenter)));
  }, [effectiveSidebar, setChatW]);

  return (
    <div className="h-screen w-screen bg-[#030405] text-on-background font-manrope overflow-hidden relative">
      {/* Ambient background glows (Lumina identity) */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-20%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-primary opacity-[0.03] blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[60vw] h-[60vw] rounded-full bg-secondary-fixed opacity-[0.02] blur-[150px]" />
      </div>

      <div ref={containerRef} className="relative z-10 flex h-full w-full">
        {/* LEFT: Sidebar */}
        <div className="h-full shrink-0" style={{ width: effectiveSidebar }}>
          <Sidebar />
        </div>
        {!sidebarCollapsed && <ResizeDivider onResize={resizeSidebar} />}

        {/* CENTER: TopBar + routed page (flexible remainder) */}
        <div className="flex h-full min-w-0 flex-1 flex-col">
          <TopBar />
          <main className="flex-1 min-h-0 overflow-y-auto scrollbar-hide p-6">
            <div className="mx-auto w-full max-w-[1400px]">
              <Page />
            </div>
          </main>
        </div>
        {showChatPanel && <ResizeDivider onResize={resizeChat} />}

        {/* RIGHT: Chat (hidden on Home/Chat pages — see route.noChatPanel) */}
        {showChatPanel && (
          <div className="h-full shrink-0" style={{ width: chatW }}>
            <ChatPanel />
          </div>
        )}
      </div>

      {/* Global overlays (fire from any page). */}
      <ConfirmationOverlay />
      <AlarmOverlay />
    </div>
  );
}

export default AppShell;
