// frontend/stores/useMemoryStore.js
// Owns memory list + stats state. No socket interaction (useMemory hook feeds it).
import { create } from 'zustand';

export const useMemoryStore = create((set) => ({
  memories: [],
  stats: null,
  loading: true,

  setMemories: (list) => set({ memories: Array.isArray(list) ? list : [], loading: false }),
  setStats: (stats) => set({ stats: stats || null }),
  // Server confirms an add via memory_added; prepend if not already present.
  addMemory: (mem) =>
    set((s) => (s.memories.some((m) => m.id === mem.id) ? s : { memories: [mem, ...s.memories] })),
  clear: () => set({ memories: [], stats: null, loading: false }),
}));

export default useMemoryStore;
