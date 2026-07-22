// frontend/components/chat/MessageBubble.jsx — pure presentational bubble
import React from 'react';
import { cn } from '../../utils/cn';

export function MessageBubble({ sender, text, time, streaming }) {
  const isUser = sender === 'You';
  return (
    <div className={cn('flex flex-col max-w-[78%]', isUser ? 'items-end self-end' : 'items-start self-start')}>
      <div
        className={cn(
          'rounded-2xl px-4 py-2.5 text-sm leading-relaxed border backdrop-blur-md',
          isUser
            ? 'bg-primary-container/15 border-primary-container/30 text-on-surface rounded-br-sm'
            : 'bg-white/[0.04] border-white/10 text-on-surface-variant rounded-bl-sm'
        )}
      >
        {text}
        {streaming && <span className="ml-1 inline-block w-1.5 h-3.5 align-middle bg-primary/70 animate-pulse rounded-sm" />}
      </div>
      <div className="mt-1 px-1 text-[10px] font-mono text-on-surface-variant/40">
        {sender} · {time}
      </div>
    </div>
  );
}

export default MessageBubble;
