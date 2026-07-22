// frontend/utils/paths.js — dot-notation get/set for nested settings objects

/** Read a nested value by dot path. Returns fallback if any segment missing. */
export function getPath(obj, path, fallback = undefined) {
  if (!obj || !path) return fallback;
  const parts = String(path).split('.');
  let cur = obj;
  for (const p of parts) {
    if (cur == null || typeof cur !== 'object' || !(p in cur)) return fallback;
    cur = cur[p];
  }
  return cur === undefined ? fallback : cur;
}

/**
 * Immutably set a nested value by dot path. Returns a NEW object; intermediate
 * objects along the path are shallow-cloned so Zustand/React see a fresh ref
 * only where it changed.
 */
export function setPath(obj, path, value) {
  const parts = String(path).split('.');
  const root = Array.isArray(obj) ? [...obj] : { ...(obj || {}) };
  let cur = root;
  for (let i = 0; i < parts.length - 1; i++) {
    const key = parts[i];
    const child = cur[key];
    cur[key] = child && typeof child === 'object' && !Array.isArray(child) ? { ...child } : {};
    cur = cur[key];
  }
  cur[parts[parts.length - 1]] = value;
  return root;
}
