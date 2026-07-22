// frontend/stores/useChatHistoryStore.js
// Owns the list of past conversations + the active conversation id. Does NOT
// touch socket/live state — useChatStore remains the live/active transcript
// exactly as before (untouched, so useChat/streaming behavior is unaffected).
// Switching conversations snapshots the current live messages into history,
// then restores the target conversation's messages into useChatStore.
import { create } from 'zustand';
import { ChatHistoryService } from '../services/chat/ChatHistoryService';
import { useChatStore } from './useChatStore';

const { conversations: initialConversations, activeId: initialActiveId } = ChatHistoryService.load();

function titleFor(messages) {
  const firstUser = messages.find((m) => m.sender === 'You');
  const text = (firstUser?.text || messages[0]?.text || 'New chat').trim();
  return text.length > 40 ? text.slice(0, 40) + '…' : text || 'New chat';
}

function persist(conversations, activeId) {
  ChatHistoryService.save(conversations, activeId);
}

export const useChatHistoryStore = create((set, get) => ({
  conversations: initialConversations, // [{ id, title, messages, updatedAt }]
  activeId: initialActiveId,

  /** Snapshot the live chat store's current messages into the active conversation entry. */
  _snapshotActive: () => {
    const { activeId, conversations } = get();
    if (!activeId) return conversations;
    const liveMessages = useChatStore.getState().messages;
    return conversations.map((c) => (c.id === activeId
      ? { ...c, messages: liveMessages, title: titleFor(liveMessages), updatedAt: Date.now() }
      : c));
  },

  /** Start a fresh conversation; archives the current one first (if non-empty). */
  newConversation: () => {
    const { conversations: snapshotted } = { conversations: get()._snapshotActive() };
    const liveMessages = useChatStore.getState().messages;
    const keep = liveMessages.length > 0 ? snapshotted : snapshotted.filter((c) => c.id !== get().activeId);
    const id = `c${Date.now()}`;
    const next = [{ id, title: 'New chat', messages: [], updatedAt: Date.now() }, ...keep];
    useChatStore.setState({ messages: [], loading: false });
    set({ conversations: next, activeId: id });
    persist(next, id);
  },

  /** Switch to an existing conversation by id. */
  switchTo: (id) => {
    const { activeId, conversations } = get();
    if (id === activeId) return;
    const snapshotted = get()._snapshotActive();
    const target = snapshotted.find((c) => c.id === id);
    useChatStore.setState({ messages: target ? target.messages : [], loading: false });
    set({ conversations: snapshotted, activeId: id });
    persist(snapshotted, id);
  },

  rename: (id, title) => {
    const next = get().conversations.map((c) => (c.id === id ? { ...c, title: title.trim() || c.title } : c));
    set({ conversations: next });
    persist(next, get().activeId);
  },

  remove: (id) => {
    const { activeId } = get();
    const next = get().conversations.filter((c) => c.id !== id);
    if (id === activeId) {
      const fallback = next[0];
      useChatStore.setState({ messages: fallback ? fallback.messages : [], loading: false });
      set({ conversations: next, activeId: fallback ? fallback.id : null });
      persist(next, fallback ? fallback.id : null);
    } else {
      set({ conversations: next });
      persist(next, activeId);
    }
  },

  /** Call periodically (e.g. on message change) to keep the active entry's snapshot fresh. */
  syncActive: () => {
    const { activeId } = get();
    if (!activeId) {
      // First message ever sent with no conversation yet — create one implicitly.
      const liveMessages = useChatStore.getState().messages;
      if (liveMessages.length === 0) return;
      const id = `c${Date.now()}`;
      const entry = { id, title: titleFor(liveMessages), messages: liveMessages, updatedAt: Date.now() };
      const next = [entry, ...get().conversations];
      set({ conversations: next, activeId: id });
      persist(next, id);
      return;
    }
    const next = get()._snapshotActive();
    set({ conversations: next });
    persist(next, activeId);
  },
}));

export default useChatHistoryStore;
