// frontend/pages/ChatPage.jsx — conversation history page (no browser/BrowserView).
// Left: conversation list. Right: active thread. Presentation only.
import React, { useEffect, useRef, useState } from 'react';
import { MessageSquare, Plus, Trash2 } from 'lucide-react';
import { GlassCard, SearchBox } from '../components/ui';
import { ChatMessage, TypingIndicator, MessageInput } from '../components/chat';
import { UploadButton } from '../components/upload';
import { useChat } from '../hooks/useChat';
import { useChatHistory } from '../hooks/useChatHistory';
import { useFileUpload } from '../hooks/useFileUpload';
import { useConnectionStatus } from '../hooks/useConnectionStatus';
import { cn } from '../utils/cn';

export default function ChatPage() {
  const { messages, loading, send } = useChat();
  const { conversations, activeId, newConversation, switchTo, remove } = useChatHistory();
  const { uploadFile } = useFileUpload();
  const { isConnected } = useConnectionStatus();
  const [search, setSearch] = useState('');
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);

  const filtered = conversations.filter((c) => c.title.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="flex h-[calc(100vh-9rem)] gap-4">
      {/* Conversation list */}
      <div className="flex w-64 shrink-0 flex-col gap-3">
        <button
          onClick={newConversation}
          className="flex items-center justify-center gap-2 rounded-xl border border-primary-container/30 bg-primary-container/10 py-2 text-xs text-primary hover:bg-primary-container/20"
        >
          <Plus size={14} /> New Chat
        </button>
        <SearchBox value={search} onChange={setSearch} placeholder="Search conversations…" />
        <div className="flex flex-1 flex-col gap-1 overflow-y-auto scrollbar-hide">
          {filtered.length === 0 ? (
            <div className="p-4 text-center text-xs text-on-surface-variant/40">No conversations yet</div>
          ) : (
            filtered.map((c) => (
              <button
                key={c.id}
                onClick={() => switchTo(c.id)}
                className={cn(
                  'group flex items-center gap-2 rounded-lg px-3 py-2 text-left text-xs transition-colors',
                  c.id === activeId ? 'bg-primary-container/10 text-primary' : 'text-on-surface-variant hover:bg-white/5 hover:text-white'
                )}
              >
                <MessageSquare size={12} className="shrink-0 opacity-60" />
                <span className="flex-1 truncate">{c.title}</span>
                <span
                  role="button" tabIndex={-1}
                  onClick={(e) => { e.stopPropagation(); remove(c.id); }}
                  className="shrink-0 rounded p-0.5 opacity-0 hover:text-red-400 group-hover:opacity-100"
                >
                  <Trash2 size={11} />
                </span>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Active thread */}
      <GlassCard className="flex flex-1 min-w-0 flex-col p-4">
        <div className="flex flex-1 min-h-0 flex-col gap-3 overflow-y-auto scrollbar-hide pr-1">
          {messages.length === 0 ? (
            <div className="flex flex-1 flex-col items-center justify-center text-center">
              <MessageSquare size={20} className="mb-3 text-on-surface-variant/40" />
              <p className="text-sm text-on-surface-variant/60">Start a conversation with Lumina.</p>
            </div>
          ) : (
            messages.map((m) => <ChatMessage key={m.id} message={m} />)
          )}
          {loading && <TypingIndicator />}
          <div ref={endRef} />
        </div>
        <div className="pt-3">
          <MessageInput
            onSend={send}
            disabled={!isConnected}
            leading={<UploadButton onFile={uploadFile} disabled={!isConnected} />}
          />
        </div>
      </GlassCard>
    </div>
  );
}
