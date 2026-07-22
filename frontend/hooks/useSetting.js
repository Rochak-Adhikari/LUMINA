// frontend/hooks/useSetting.js
// Per-path settings binding. A component using useSetting('vad_min_speech_ms')
// rerenders ONLY when that path changes (Zustand selector), not on any setting.
import { useCallback } from 'react';
import { useSettingsStore } from '../stores/useSettingsStore';
import { getPath } from '../utils/paths';

/**
 * @param {string} path  dot path, e.g. 'tool_permissions.browser_control'
 * @param {*} [fallback]
 * @returns {[*, (value:*) => void]} [value, setValue]
 */
export function useSetting(path, fallback) {
  const value = useSettingsStore((s) => getPath(s.settings, path, fallback));
  const setFn = useSettingsStore((s) => s.set);
  const setValue = useCallback((v) => setFn(path, v), [setFn, path]);
  return [value, setValue];
}

/** Subscribe to save/dirty status only. Each field is selected individually so
 *  the selector never returns a new object (a new object every render triggers
 *  useSyncExternalStore's "getSnapshot should be cached" infinite loop). */
export function useSettingsStatus() {
  const dirty = useSettingsStore((s) => s.dirty);
  const saving = useSettingsStore((s) => s.saving);
  const loaded = useSettingsStore((s) => s.loaded);
  const lastSaved = useSettingsStore((s) => s.lastSaved);
  const error = useSettingsStore((s) => s.error);
  return { dirty, saving, loaded, lastSaved, error };
}

export default useSetting;
