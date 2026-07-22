// frontend/components/chat/TypingIndicator.jsx — assistant thinking dots
import React from 'react';

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 self-start rounded-2xl rounded-bl-sm border border-white/10 bg-white/[0.04] px-4 py-3 backdrop-blur-md">
      {[0, 150, 300].map((d) => (
        <span
          key={d}
          className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce"
          style={{ animationDelay: `${d}ms` }}
        />
      ))}
    </div>
  );
}

export default TypingIndicator;
