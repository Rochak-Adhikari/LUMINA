// frontend/hooks/useConnectionStatus.js
// Subscribe to the derived connection-status machine. Returns one of
// 'connecting' | 'connected' | 'disconnected' plus convenience booleans.
// Uses useSyncExternalStore so the value stays consistent across renders.
import { useSyncExternalStore } from 'react';
import { subscribeStatus, getStatus } from '../services/socketManager';

export function useConnectionStatus() {
  const status = useSyncExternalStore(subscribeStatus, getStatus, getStatus);
  return {
    status,
    isConnected: status === 'connected',
    isConnecting: status === 'connecting',
    isDisconnected: status === 'disconnected',
  };
}

export default useConnectionStatus;
