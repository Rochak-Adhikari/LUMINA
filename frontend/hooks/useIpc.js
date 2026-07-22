// frontend/hooks/useIpc.js
// Thin wrapper over ipcManager (mirror of useSocket). Stable identity.
import { useMemo } from 'react';
import { invoke, send, isElectron } from '../services/ipcManager';

export function useIpc() {
  return useMemo(() => ({ invoke, send, isElectron: isElectron() }), []);
}

export default useIpc;
