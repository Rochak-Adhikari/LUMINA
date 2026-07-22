// frontend/components/chat/MessageInput.jsx — controlled input + send
import React, { useState } from 'react';
import { Send } from 'lucide-react';
import { cn } from '../../utils/cn';

export function MessageInput({ onSend, disabled, leading }) {
  const [value, setValue] = useState('');

  const submit = () => {
    const text = value.trim();
    if (!text) return;
    const ok = onSend(text);
    if (ok !== false) setValue('');
  };

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2.5 backdrop-blur-md">
      {leading}
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKey}
        placeholder={disabled ? 'Disconnected — reconnecting…' : 'Message Lumina…'}
        disabled={disabled}
        className="flex-1 bg-transparent border-0 outline-none text-sm text-on-surface placeholder-on-surface-variant/40 focus:ring-0 disabled:opacity-50"
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        className={cn(
          'p-2 rounded-full border transition-all duration-200',
          value.trim() && !disabled
            ? 'border-primary-container/40 bg-primary-container/20 text-primary hover:scale-105'
            : 'border-transparent text-on-surface-variant/20'
        )}
      >
        <Send size={14} />
      </button>
    </div>
  );
}

export default MessageInput;
