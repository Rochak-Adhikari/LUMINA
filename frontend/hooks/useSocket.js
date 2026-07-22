// frontend/hooks/useSocket.js
// Access the shared socket API (emit + typed event name maps) without touching
// the client directly. Stable identity — safe in deps.
import { useMemo } from 'react';
import { emit, isConnected, EMIT, ON } from '../services/socketManager';

export function useSocket() {
  return useMemo(() => ({ emit, isConnected, EMIT, ON }), []);
}

export default useSocket;
