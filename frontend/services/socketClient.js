// frontend/services/socketClient.js
// Single process-wide Socket.IO client. Auto-connect + auto-reconnect. The
// heartbeat (backend hb_ping -> client hb_pong) is registered once here so it
// survives all component churn. No page-specific logic lives in this module.
import io from 'socket.io-client';
import { BASE_URL, EMIT, ON } from './endpoints';

export const socket = io(BASE_URL, {
  autoConnect: true,
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 500,
  reconnectionDelayMax: 5000,
});

// Heartbeat — registered once, independent of any component.
socket.on(ON.hbPing, () => socket.emit(EMIT.hbPong));

export { EMIT, ON };
export default socket;
