// frontend/services/ipcClient.js
// Lowest layer: safe access to Electron's ipcRenderer. Detects Electron once,
// and every primitive is a no-op when unavailable (browser preview) so nothing
// throws. No Browser logic, no dedup, no state — that lives in ipcManager.

function resolveIpc() {
  try {
    if (typeof window !== 'undefined' && typeof window.require === 'function') {
      const electron = window.require('electron');
      return electron?.ipcRenderer || null;
    }
  } catch {
    /* not running under Electron */
  }
  return null;
}

const ipcRenderer = resolveIpc();

export const isElectron = () => ipcRenderer !== null;

export function invoke(channel, payload) {
  if (!ipcRenderer) return Promise.reject(new Error('IPC unavailable (not running in Electron)'));
  return ipcRenderer.invoke(channel, payload);
}

export function send(channel, payload) {
  if (!ipcRenderer) return false;
  ipcRenderer.send(channel, payload);
  return true;
}

export function on(channel, listener) {
  if (!ipcRenderer) return () => {};
  ipcRenderer.on(channel, listener);
  return () => ipcRenderer.removeListener(channel, listener);
}

export function removeListener(channel, listener) {
  if (!ipcRenderer) return;
  ipcRenderer.removeListener(channel, listener);
}

export default { isElectron, invoke, send, on, removeListener };
