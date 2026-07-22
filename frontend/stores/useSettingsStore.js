// frontend/stores/useSettingsStore.js
// Centralized settings store. Single owner of the config object — no component
// reads/writes JSON directly. Supports nested dot paths, debounced autosave,
// dirty/saving/loaded state, reset/import/export.
import { create } from 'zustand';
import { SettingsService } from '../services/settings/SettingsService';
import { cloneDefaults } from '../defaults/defaultSettings';
import { getPath, setPath } from '../utils/paths';

const AUTOSAVE_MS = 400; // debounce window (300–500ms range)
let _saveTimer = null;

export const useSettingsStore = create((set, get) => ({
  settings: cloneDefaults(),
  loaded: false,
  dirty: false,
  saving: false,
  lastSaved: null,
  error: null,

  /** Load from persistence into the store. Call once on app mount. */
  load: async () => {
    try {
      const settings = await SettingsService.load();
      set({ settings, loaded: true, dirty: false, error: null });
    } catch (e) {
      set({ loaded: true, error: e.message || String(e) });
    }
  },

  /** Read a value by dot path. */
  get: (path, fallback) => getPath(get().settings, path, fallback),

  /** Write a value by dot path → marks dirty → schedules debounced autosave. */
  set: (path, value) => {
    const next = setPath(get().settings, path, value);
    set({ settings: next, dirty: true });
    get()._scheduleSave();
  },

  /** Debounced autosave: many edits collapse into one save. */
  _scheduleSave: () => {
    if (_saveTimer) clearTimeout(_saveTimer);
    _saveTimer = setTimeout(() => { get().save(); }, AUTOSAVE_MS);
  },

  /** Persist immediately. */
  save: async () => {
    if (_saveTimer) { clearTimeout(_saveTimer); _saveTimer = null; }
    set({ saving: true });
    try {
      await SettingsService.save(get().settings);
      set({ saving: false, dirty: false, lastSaved: Date.now(), error: null });
    } catch (e) {
      set({ saving: false, error: e.message || String(e) });
    }
  },

  /** Re-read from persistence, discarding unsaved changes. */
  reload: async () => {
    set({ loaded: false });
    await get().load();
  },

  /** Reset to defaults (in memory) + autosave. */
  reset: () => {
    set({ settings: cloneDefaults(), dirty: true });
    get()._scheduleSave();
  },

  /** Serialize current config for download/copy. */
  exportConfig: () => JSON.stringify(get().settings, null, 2),

  /** Apply a config from JSON text. Returns true on success. */
  importConfig: (json) => {
    try {
      const parsed = JSON.parse(json);
      if (!parsed || typeof parsed !== 'object') return false;
      set({ settings: parsed, dirty: true, error: null });
      get()._scheduleSave();
      return true;
    } catch {
      return false;
    }
  },
}));

// Selector helper: subscribe to ONE path so only affected components rerender.
export const useSettingValue = (path, fallback) =>
  useSettingsStore((s) => getPath(s.settings, path, fallback));

export default useSettingsStore;
