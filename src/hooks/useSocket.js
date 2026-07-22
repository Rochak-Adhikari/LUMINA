// hooks/useSocket.js — subscribe to a Socket.IO event with automatic cleanup.
// Prevents duplicate listeners (off before on) and removes on unmount.
import { useEffect } from 'react';
import socket from '../services/socket';

export function useSocketEvent(event, handler, deps = []) {
  useEffect(() => {
    if (!event || typeof handler !== 'function') return undefined;
    socket.off(event, handler);
    socket.on(event, handler);
    return () => socket.off(event, handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event, ...deps]);
}

// Access the shared socket + a stable emit helper.
export function useSocket() {
  return { socket, emit: (e, p, ack) => socket.emit(e, p, ack), connected: socket.connected };
}

export default useSocket;
