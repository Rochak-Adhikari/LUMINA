// frontend/hooks/useChat.js
// Sole owner of chat socket interaction. Bridges the shared socket layer to the
// chat store. All listeners go through useSocketEvent (reference-counted,
// auto-cleanup, reconnect-safe). No direct socket.io usage.
import { useCallback } from 'react';
import { useSocket } from './useSocket';
import { useSocketEvent } from './useSocketEvent';
import { useChatStore } from '../stores/useChatStore';

export function useChat() {
  const { emit, EMIT, ON } = useSocket();

  const messages = useChatStore((s) => s.messages);
  const loading = useChatStore((s) => s.loading);
  const addUserMessage = useChatStore((s) => s.addUserMessage);
  const appendTranscript = useChatStore((s) => s.appendTranscript);
  const addMessage = useChatStore((s) => s.addMessage);

  // Streaming voice/assistant transcript chunks.
  useSocketEvent(ON.transcription, (data) => {
    if (!data || !data.text) return;
    appendTranscript(data.sender || 'Lumina', data.text);
  });

  // Complete chat messages (system/assistant).
  useSocketEvent(ON.chatMessage, (data) => {
    if (!data) return;
    addMessage(data.sender || 'System', data.text || '');
  });

  const send = useCallback(
    (text) => {
      const trimmed = (text || '').trim();
      if (!trimmed) return false;
      addUserMessage(trimmed);
      emit(EMIT.userInput, { text: trimmed });
      return true;
    },
    [emit, EMIT, addUserMessage]
  );

  return { messages, loading, send };
}

export default useChat;
