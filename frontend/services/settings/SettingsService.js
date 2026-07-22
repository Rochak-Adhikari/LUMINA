// frontend/services/settings/SettingsService.js
// Persistence abstraction. This phase: localStorage (survives app restart, no
// backend). When SettingsIPC becomes available it is preferred automatically —
// the store never changes.
import { SettingsIPC } from './SettingsIPC';
import { cloneDefaults } from '../../defaults/defaultSettings';

const STORAGE_KEY = 'lumina_settings';

/** Merge saved settings over defaults so new default keys always appear. */
function mergeWithDefaults(saved) {
  const base = cloneDefaults();
  if (!saved || typeof saved !== 'object') return base;
  const out = { ...base, ...saved };
  // deep-merge tool_permissions so new permission keys are not lost
  out.tool_permissions = { ...base.tool_permissions, ...(saved.tool_permissions || {}) };
  return out;
}

export const SettingsService = {
  /** Load settings. Prefers backend IPC when available, else localStorage. */
  async load() {
    try {
      if (SettingsIPC.available()) {
        const remote = await SettingsIPC.load();
        if (remote) {
          const merged = mergeWithDefaults(remote);
          // Refresh the local cache so a later offline start has fresh values.
          try { localStorage.setItem(STORAGE_KEY, JSON.stringify(merged)); } catch { /* ignore */ }
          return merged;
        }
      }
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return mergeWithDefaults(JSON.parse(raw));
      return cloneDefaults();
    } catch (e) {
      // Surface a real error so the UI can offer Retry / Restore Defaults.
      throw new Error('Failed to load settings: ' + (e && e.message || e));
    }
  },

  /** Persist settings. Writes localStorage now; also pushes to IPC if present. */
  async save(settings) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
      if (SettingsIPC.available()) await SettingsIPC.save(settings);
      return true;
    } catch (e) {
      throw new Error('Failed to save settings: ' + (e && e.message || e));
    }
  },

  /** Reset persisted store (does not itself write defaults back). */
  async clear() {
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
  },
};

export default SettingsService;
