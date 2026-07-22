// frontend/services/chat/ChatHistoryService.js
// Modular persistence for chat conversation history. localStorage-backed now;
// swap this module for a backend API later without touching the store/UI.
const KEY = 'lumina_conversations';

function safeParse(raw, fallback) {
  try { const v = JSON.parse(raw); return v ?? fallback; } catch { return fallback; }
}

export const ChatHistoryService = {
  /** @returns {{conversations: Array, activeId: string|null}} */
  load() {
    if (typeof localStorage === 'undefined') return { conversations: [], activeId: null };
    const data = safeParse(localStorage.getItem(KEY), null);
    if (!data || !Array.isArray(data.conversations)) return { conversations: [], activeId: null };
    return { conversations: data.conversations, activeId: data.activeId ?? null };
  },

  save(conversations, activeId) {
    if (typeof localStorage === 'undefined') return;
    try { localStorage.setItem(KEY, JSON.stringify({ conversations, activeId })); } catch { /* quota — non-fatal */ }
  },

  clear() {
    if (typeof localStorage === 'undefined') return;
    try { localStorage.removeItem(KEY); } catch { /* ignore */ }
  },
};

export default ChatHistoryService;
