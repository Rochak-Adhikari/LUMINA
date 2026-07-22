// frontend/services/socketManager.js
// Thin coordination layer over the single socketClient. Responsibilities:
//   - one subscribe/emit API for hooks (no component touches socket directly)
//   - reference-counted listeners so N subscribers = 1 underlying socket.on
//   - a derived connection-status machine (connecting/connected/disconnected)
//     with its own subscribe API for useConnectionStatus
// No page-specific logic. No Chat/Browser/Workspace knowledge.
import { socket, EMIT, ON } from './socketClient';

// ── Connection status machine ──────────────────────────────────────────────
// 'connecting' | 'connected' | 'disconnected'
let status = socket.connected ? 'connected' : 'connecting';
const statusListeners = new Set();

function setStatus(next) {
  if (status === next) return;
  status = next;
  statusListeners.forEach((fn) => fn(status));
}

socket.on('connect', () => setStatus('connected'));
socket.on('disconnect', () => setStatus('disconnected'));
socket.io.on('reconnect_attempt', () => setStatus('connecting'));
socket.io.on('reconnect', () => setStatus('connected'));

export function getStatus() {
  return status;
}

export function subscribeStatus(listener) {
  statusListeners.add(listener);
  listener(status); // emit current value immediately
  return () => statusListeners.delete(listener);
}

// ── Event subscription with reference counting ─────────────────────────────
// Map<event, { handler, subscribers:Set<fn> }>. One real socket.on per event;
// each subscriber's callback is invoked via the shared fan-out handler.
const registry = new Map();

export function subscribe(event, callback) {
  let entry = registry.get(event);
  if (!entry) {
    const subscribers = new Set();
    const handler = (...args) => subscribers.forEach((fn) => fn(...args));
    socket.on(event, handler);
    entry = { handler, subscribers };
    registry.set(event, entry);
  }
  entry.subscribers.add(callback);

  return () => {
    const e = registry.get(event);
    if (!e) return;
    e.subscribers.delete(callback);
    if (e.subscribers.size === 0) {
      socket.off(event, e.handler);
      registry.delete(event);
    }
  };
}

export function emit(event, payload, ack) {
  // Only forward args that were actually provided. socket.io-client serializes
  // trailing `undefined` as `null` DATA arguments (undefined -> null on the
  // wire), so emit('get_settings', undefined, undefined) reaches the server as
  // get_settings(sid, None, None) — a 3-arg call that raises
  // "TypeError: get_settings() takes 1 positional argument but 3 were given".
  // Passing only the supplied args keeps the wire packet arity correct:
  //   emit('get_settings')            -> ["get_settings"]
  //   emit('update_settings', data)   -> ["update_settings", data]
  //   emit('x', data, ackFn)          -> ["x", data] + ack callback
  if (typeof ack === 'function') {
    return payload !== undefined ? socket.emit(event, payload, ack) : socket.emit(event, ack);
  }
  if (payload !== undefined) return socket.emit(event, payload);
  return socket.emit(event);
}

export function isConnected() {
  return socket.connected;
}

export { socket, EMIT, ON };
