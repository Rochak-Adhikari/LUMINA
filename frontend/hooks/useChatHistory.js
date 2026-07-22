// frontend/hooks/useChatHistory.js
// Bridges the live chat store (useChatStore) to the conversation-history store.
// Keeps the active conversation's snapshot fresh as messages arrive/stream, and
// exposes new/switch/rename/remove actions. No socket logic — purely local
// persistence (ChatHistoryService). No JSX.
import { useEffect, useRef } from 'react';
import { useChatStore } from '../stores/useChatStore';
import { useChatHistoryStore } from '../stores/useChatHistoryStore';

export function useChatHistory() {
  const conversations = useChatHistoryStore((s) => s.conversations);
  const activeId = useChatHistoryStore((s) => s.activeId);
  const newConversation = useChatHistoryStore((s) => s.newConversation);
  const switchTo = useChatHistoryStore((s) => s.switchTo);
  const rename = useChatHistoryStore((s) => s.rename);
  const remove = useChatHistoryStore((s) => s.remove);
  const syncActive = useChatHistoryStore((s) => s.syncActive);

  const messages = useChatStore((s) => s.messages);
  const debounceRef = useRef(null);

  // Debounced sync so a streaming burst of chunks doesn't hammer localStorage.
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => syncActive(), 500);
    return () => clearTimeout(debounceRef.current);
  }, [messages, syncActive]);

  return { conversations, activeId, newConversation, switchTo, rename, remove };
}

export default useChatHistory;
