// frontend/hooks/useMemory.js
// Sole owner of memory socket interaction. Bridges the shared socket layer to
// the memory store. Read (get_memories -> memories, get_memory_stats ->
// memory_stats) + add (add_memory -> memory_added). No direct socket.io.
import { useCallback, useEffect } from 'react';
import { useSocket } from './useSocket';
import { useSocketEvent } from './useSocketEvent';
import { useMemoryStore } from '../stores/useMemoryStore';

export function useMemory() {
  const { emit, EMIT } = useSocket();

  const memories = useMemoryStore((s) => s.memories);
  const stats = useMemoryStore((s) => s.stats);
  const loading = useMemoryStore((s) => s.loading);
  const setMemories = useMemoryStore((s) => s.setMemories);
  const setStats = useMemoryStore((s) => s.setStats);
  const addMemoryToStore = useMemoryStore((s) => s.addMemory);

  const refetch = useCallback(() => {
    emit(EMIT.getMemories, { limit: 50 });
    emit(EMIT.getMemoryStats);
  }, [emit, EMIT]);

  useEffect(() => { refetch(); }, [refetch]);
  useSocketEvent('connect', refetch); // reconnect-safe re-fetch

  // Server payload: { memories: [...] }
  useSocketEvent('memories', (data) => setMemories(data?.memories || []));
  useSocketEvent('memory_stats', (data) => setStats(data || null));
  useSocketEvent('memory_added', (mem) => { if (mem) addMemoryToStore(mem); });

  const add = useCallback(
    (type, content, metadata) => {
      if (!type || !content) return false;
      emit(EMIT.addMemory, { type, content, metadata });
      return true;
    },
    [emit, EMIT]
  );

  return { memories, stats, loading, add, refetch };
}

export default useMemory;
