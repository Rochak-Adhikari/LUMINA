// frontend/layout/ChatPanel.jsx — always-visible RIGHT column. Presentation
// only: composes useChat (messages/streaming), useVoice (mic/power session),
// useFileUpload (attachments), and useChatHistory (local conversation list).
// Home + Chat are merged here — there is no separate Home/Chat page anymore.
import React, { useEffect, useRef, useState } from 'react';
import { MessageSquare, Mic, MicOff, Power } from 'lucide-react';
import { ChatMessage, TypingIndicator, MessageInput, ConversationHistory } from '../components/chat';
import { UploadButton } from '../components/upload';
import { useChat } from '../hooks/useChat';
import { useVoice } from '../hooks/useVoice';
import { useFileUpload } from '../hooks/useFileUpload';
import { useChatHistory } from '../hooks/useChatHistory';
import { useConnectionStatus } from '../hooks/useConnectionStatus';
import { cn } from '../utils/cn';

export function ChatPanel() {
  const { messages, loading, send } = useChat();
  const v = useVoice();
  const { uploadFile } = useFileUpload();
  const history = useChatHistory();
  const { isConnected, status } = useConnectionStatus();
  const [historyOpen, setHistoryOpen] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  return (
    <div className="flex h-full min-h-0 w-full flex-col border-l border-white/5 bg-surface-container-lowest/40 backdrop-blur-2xl">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-white/5 px-4 py-3">
        <div className="flex items-center gap-2">
          <MessageSquare size={16} className="text-primary" />
          <span className="font-sora text-sm font-semibold text-on-surface">Chat</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[10px] uppercase tracking-widest text-on-surface-variant/50">{status}</span>
          <button
            onClick={() => setHistoryOpen((o) => !o)}
            className={cn('rounded-lg px-2 py-1 text-[10px] font-mono uppercase tracking-widest transition-colors',
              historyOpen ? 'bg-primary-container/15 text-primary' : 'text-on-surface-variant hover:text-primary')}
          >
            History
          </button>
        </div>
      </div>

      {historyOpen && (
        <div className="shrink-0 border-b border-white/5 px-3 py-2">
          <ConversationHistory
            conversations={history.conversations}
            activeId={history.activeId}
            onNew={history.newConversation}
            onSwitch={history.switchTo}
            onRemove={history.remove}
          />
        </div>
      )}

      {/* Voice session strip */}
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-white/5 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className={cn('h-2 w-2 rounded-full',
            v.modelStatus === 'connected' ? 'bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.5)]'
              : v.connected ? 'bg-yellow-400 animate-pulse' : 'bg-red-400')} />
          <span className="font-mono text-[10px] uppercase tracking-widest text-primary/70">{v.statusText}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={v.togglePower}
            disabled={!v.socketConnected}
            title={v.connected ? 'End voice session' : 'Start voice session'}
            className={cn('rounded-lg border p-1.5 transition-all',
              v.connected ? 'border-green-500/40 bg-green-500/10 text-green-300' : 'border-white/10 text-on-surface-variant hover:text-white disabled:opacity-40')}
          >
            <Power size={13} />
          </button>
          <button
            onClick={v.toggleMute}
            disabled={!v.connected}
            title={v.muted ? 'Unmute' : 'Mute'}
            className={cn('rounded-lg border p-1.5 transition-all',
              !v.connected ? 'border-transparent text-on-surface-variant/30'
                : v.muted ? 'border-red-500/40 bg-red-500/10 text-red-300' : 'border-primary-container/40 bg-primary-container/20 text-primary')}
          >
            {v.muted ? <MicOff size={13} /> : <Mic size={13} />}
          </button>
        </div>
      </div>

      {/* Message list */}
      <div className="flex flex-1 min-h-0 flex-col gap-3 overflow-y-auto scrollbar-hide px-3 py-3">
        {messages.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center text-center">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-white/10">
              <MessageSquare size={20} className="text-on-surface-variant/40" />
            </div>
            <p className="text-sm text-on-surface-variant/60">Start a conversation with Lumina.</p>
          </div>
        ) : (
          messages.map((m) => <ChatMessage key={m.id} message={m} />)
        )}
        {loading && <TypingIndicator />}
        <div ref={endRef} />
      </div>

      {/* Composer */}
      <div className="shrink-0 px-3 pb-3 pt-1">
        <MessageInput
          onSend={send}
          disabled={!isConnected}
          leading={<UploadButton onFile={uploadFile} disabled={!isConnected} />}
        />
      </div>
    </div>
  );
}

export default ChatPanel;
