// services/socket.js — single shared Socket.IO connection to the live backend.
// All UI communicates through this module instead of constructing io() inline.
import io from 'socket.io-client';
import { BASE_URL, EMIT, ON } from './endpoints';

// One process-wide connection. Reconnection is enabled so a backend restart
// (or a slow first boot) recovers without a page reload.
export const socket = io(BASE_URL, {
  autoConnect: true,
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 500,
  reconnectionDelayMax: 5000,
});

// Heartbeat: backend emits hb_ping, expects hb_pong. Registered once here so
// it survives regardless of component mount/unmount churn.
socket.on(ON.hbPing, () => socket.emit(EMIT.hbPong));

export const emit = (event, payload, ack) => socket.emit(event, payload, ack);
export const on = (event, handler) => { socket.on(event, handler); return () => socket.off(event, handler); };
export const off = (event, handler) => socket.off(event, handler);
export const isConnected = () => socket.connected;

export { EMIT, ON };
export default socket;
