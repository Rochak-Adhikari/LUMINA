// frontend/stores/useVoiceStore.js
// Owns voice-session state. No socket interaction (useVoice hook feeds it).
// Mirrors the store/hook split used by chat + memory.
import { create } from 'zustand';

export const useVoiceStore = create((set) => ({
  connected: false,          // audio session active (start_audio acked / running)
  muted: true,               // mic paused
  modelStatus: 'disconnected', // Gemini live model: disconnected | connecting | connected
  statusText: 'Disconnected',
  aiAudioData: new Array(64).fill(0), // latest AI audio spectrum frame (visualizer)

  setConnected: (connected) => set({ connected }),
  setMuted: (muted) => set({ muted }),
  setModelStatus: (modelStatus) => set({ modelStatus }),
  setStatusText: (statusText) => set({ statusText }),
  setAiAudioData: (aiAudioData) => set({ aiAudioData: Array.isArray(aiAudioData) ? aiAudioData : [] }),
}));

export default useVoiceStore;
