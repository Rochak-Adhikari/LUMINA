// frontend/services/ipcManager.js
// Coordination layer over ipcClient (mirror of socketManager). One real
// ipcRenderer listener per channel, fanned out to N subscribers (dedup +
// reference counting). Normalizes Electron's (event, ...args) callback so
// subscribers receive only the payload. No UI, no Browser logic.
import { isElectron, invoke as clientInvoke, send as clientSend, on as clientOn } from './ipcClient';

// Map<channel, { off, subscribers:Set<fn> }>
const registry = new Map();

export function subscribe(channel, callback) {
  let entry = registry.get(channel);
  if (!entry) {
    const subscribers = new Set();
    // Strip the leading IpcRendererEvent — pass through the payload args only.
    const off = clientOn(channel, (_event, ...args) => {
      subscribers.forEach((fn) => fn(...args));
    });
    entry = { off, subscribers };
    registry.set(channel, entry);
  }
  entry.subscribers.add(callback);

  return () => {
    const e = registry.get(channel);
    if (!e) return;
    e.subscribers.delete(callback);
    if (e.subscribers.size === 0) {
      e.off();
      registry.delete(channel);
    }
  };
}

export function unsubscribe(channel, callback) {
  const e = registry.get(channel);
  if (!e) return;
  e.subscribers.delete(callback);
  if (e.subscribers.size === 0) {
    e.off();
    registry.delete(channel);
  }
}

export function invoke(channel, payload) {
  return clientInvoke(channel, payload);
}

export function send(channel, payload) {
  return clientSend(channel, payload);
}

export { isElectron };
