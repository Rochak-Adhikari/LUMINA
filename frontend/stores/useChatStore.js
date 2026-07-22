// frontend/stores/useChatStore.js
// Owns ALL chat state. No socket interaction here — the useChat hook feeds it.
// Message: { id, sender, text, time, streaming }
import { create } from 'zustand';

let seq = 0;
const nextId = () => `m${++seq}`;
const now = () => new Date().toLocaleTimeString();

export const useChatStore = create((set) => ({
  messages: [],
  loading: false, // awaiting assistant response after a user send

  // Optimistic local echo of the user's own input.
  addUserMessage: (text) =>
    set((s) => ({
      loading: true,
      messages: [...s.messages, { id: nextId(), sender: 'You', text, time: now(), streaming: false }],
    })),

  // Streaming transcript chunk. Merge into the last message if same sender is
  // still streaming; otherwise start a new streaming message.
  appendTranscript: (sender, chunk) =>
    set((s) => {
      const last = s.messages[s.messages.length - 1];
      if (last && last.sender === sender && last.streaming) {
        const merged = { ...last, text: last.text + chunk };
        return { loading: false, messages: [...s.messages.slice(0, -1), merged] };
      }
      return {
        loading: false,
        messages: [...s.messages, { id: nextId(), sender, text: chunk, time: now(), streaming: true }],
      };
    }),

  // A complete (non-streaming) message. If the last message was a streaming
  // turn from the same sender, replace it with the finalized text.
  addMessage: (sender, text) =>
    set((s) => {
      const last = s.messages[s.messages.length - 1];
      if (last && last.sender === sender && last.streaming) {
        const finalized = { ...last, text, streaming: false };
        return { loading: false, messages: [...s.messages.slice(0, -1), finalized] };
      }
      return {
        loading: false,
        messages: [...s.messages, { id: nextId(), sender, text, time: now(), streaming: false }],
      };
    }),

  // Mark any trailing streaming message complete (e.g. turn boundary).
  finalizeStreaming: () =>
    set((s) => {
      const last = s.messages[s.messages.length - 1];
      if (!last || !last.streaming) return s;
      return { messages: [...s.messages.slice(0, -1), { ...last, streaming: false }] };
    }),

  clear: () => set({ messages: [], loading: false }),
}));

export default useChatStore;
