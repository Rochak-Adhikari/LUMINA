// frontend/components/chat/ChatMessage.jsx — one message row (wraps bubble)
import React from 'react';
import { MessageBubble } from './MessageBubble';

export function ChatMessage({ message }) {
  return (
    <div className="flex w-full">
      <MessageBubble
        sender={message.sender}
        text={message.text}
        time={message.time}
        streaming={message.streaming}
      />
    </div>
  );
}

export default ChatMessage;
