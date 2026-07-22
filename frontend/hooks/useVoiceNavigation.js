// frontend/hooks/useVoiceNavigation.js
// Sole owner of voice-driven navigation socket interaction. Bridges the shared
// socket layer (Phase 5) to the nav store. Backend contract (server.py):
//   receive 'navigate_panel' -> { panel, view? }
// Backend panel names map onto new-frontend route ids; the workspace sub-panels
// (quests/events/archive) deep-link into the WorkspacePage tab via the store.
// No JSX, no direct socket.io.
import { useSocketEvent } from './useSocketEvent';
import { useSocket } from './useSocket';
import { useNavStore } from '../stores/useNavStore';

// Backend panel -> { page (route id), tab? (workspace sub-tab) }
const PANEL_MAP = {
  home: { page: 'home' },
  settings: { page: 'settings' },
  quests: { page: 'workspace', tab: 'quests' },
  events: { page: 'workspace', tab: 'events' },
  archive: { page: 'workspace', tab: 'archive' },
};

export function useVoiceNavigation() {
  const { ON } = useSocket();
  const navigateTo = useNavStore((s) => s.navigateTo);

  useSocketEvent(ON.navigatePanel, (data) => {
    const panel = data?.panel;
    if (!panel) return;
    const target = PANEL_MAP[panel];
    if (!target) return;
    navigateTo(target.page, target.tab ?? null);
  });
}

export default useVoiceNavigation;
