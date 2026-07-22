// frontend/components/chat/ConversationHistory.jsx — presentation only
import React from 'react';
import { Plus, MessageSquare, Trash2 } from 'lucide-react';
import { cn } from '../../utils/cn';

export function ConversationHistory({ conversations, activeId, onNew, onSwitch, onRemove }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between px-1 pb-1">
        <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant/50">History</span>
        <button
          onClick={onNew}
          title="New chat"
          className="rounded-lg p-1 text-on-surface-variant hover:bg-white/5 hover:text-primary transition-colors"
        >
          <Plus size={13} />
        </button>
      </div>

      {conversations.length === 0 ? (
        <div className="px-2 py-3 text-center text-[11px] text-on-surface-variant/40">
          No conversations yet
        </div>
      ) : (
        <div className="flex flex-col gap-0.5 max-h-48 overflow-y-auto scrollbar-hide">
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => onSwitch(c.id)}
              className={cn(
                'group flex items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs transition-colors',
                c.id === activeId ? 'bg-primary-container/10 text-primary' : 'text-on-surface-variant hover:bg-white/5 hover:text-white'
              )}
            >
              <MessageSquare size={12} className="shrink-0 opacity-60" />
              <span className="flex-1 truncate">{c.title}</span>
              <span
                role="button"
                tabIndex={-1}
                onClick={(e) => { e.stopPropagation(); onRemove(c.id); }}
                className="shrink-0 rounded p-0.5 opacity-0 hover:text-red-400 group-hover:opacity-100 transition-opacity"
              >
                <Trash2 size={11} />
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default ConversationHistory;
