// frontend/services/settings/SettingsIPC.js
// Real backend bridge for settings, over the shared Socket.IO layer (Phase 5).
// The backend contract (backend/server.py):
//   emit('get_settings')            -> server replies with 'settings' (full payload)
//   emit('update_settings', data)   -> server persists + re-broadcasts 'settings'
// Kept behind this interface so SettingsService/​the store never change.
import { socket } from '../socketClient';
import { subscribe, emit, isConnected } from '../socketManager';
import { EMIT, ON } from '../endpoints';

const LOAD_TIMEOUT_MS = 4000;

export const SettingsIPC = {
  /**
   * Request the current settings from the backend. Resolves with the payload,
   * or null on timeout / no connection (SettingsService then falls back).
   * @returns {Promise<Object|null>}
   */
  async load() {
    if (!isConnected()) return null;
    return new Promise((resolve) => {
      let done = false;
      const finish = (val) => { if (!done) { done = true; off(); clearTimeout(timer); resolve(val); } };
      const off = subscribe(ON.settings, (payload) => finish(payload || null));
      const timer = setTimeout(() => finish(null), LOAD_TIMEOUT_MS);
      emit(EMIT.getSettings);
    });
  },

  /**
   * Push a settings delta (or full object) to the backend. The server persists
   * to settings.json and re-broadcasts. Fire-and-forget over the socket.
   * @param {Object} settings
   * @returns {Promise<boolean>}
   */
  async save(settings) {
    if (!isConnected()) return false;
    emit(EMIT.updateSettings, settings);
    return true;
  },

  /** True when the socket is connected (backend bridge live). */
  available() {
    return isConnected();
  },

  /**
   * Subscribe to server-pushed settings broadcasts (e.g. another client or a
   * server-side change). Returns an unsubscribe fn. Used for live sync.
   * @param {(payload:Object)=>void} handler
   */
  onRemoteUpdate(handler) {
    return subscribe(ON.settings, handler);
  },
};

// keep a reference so tree-shakers don't drop the socket singleton import
void socket;

export default SettingsIPC;
