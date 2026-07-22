// frontend/pages/Diagnostics/systemInfo.js
// Data/logic module for the Diagnostics page. Pure, client-side only — reads
// navigator/screen APIs available in the renderer. No socket, no IPC, no
// localStorage. Every accessor is guarded so it is safe under Node (build/test).

const UNKNOWN = 'Unknown';

const nav = () => (typeof navigator !== 'undefined' ? navigator : null);
const scr = () => (typeof screen !== 'undefined' ? screen : null);
const win = () => (typeof window !== 'undefined' ? window : null);

/**
 * Extract Chromium / Electron versions from a userAgent string.
 * Electron UAs look like: ...Chrome/150.0.0.0 ... Electron/43.1.1 ...
 */
export function parseUserAgent(ua = '') {
  const chromium = /Chrome\/([\d.]+)/.exec(ua)?.[1] || UNKNOWN;
  const electron = /Electron\/([\d.]+)/.exec(ua)?.[1] || null;
  return { chromium, electron };
}

/** Runtime versions (Chromium/Electron), derived from the userAgent. */
export function getRuntimeInfo() {
  const ua = nav()?.userAgent || '';
  const { chromium, electron } = parseUserAgent(ua);
  return {
    chromium,
    electron: electron || 'N/A (browser)',
    isElectron: !!electron,
  };
}

/** Host environment: platform, CPU, memory, language, connectivity. */
export function getEnvironmentInfo() {
  const n = nav();
  const cores = n?.hardwareConcurrency;
  const mem = n?.deviceMemory;
  return {
    platform: n?.platform || UNKNOWN,
    cores: typeof cores === 'number' ? cores : null,
    memoryGb: typeof mem === 'number' ? mem : null,
    language: n?.language || UNKNOWN,
    online: typeof n?.onLine === 'boolean' ? n.onLine : null,
  };
}

/** Display geometry: resolution, viewport, pixel ratio. */
export function getDisplayInfo() {
  const s = scr();
  const w = win();
  return {
    resolution: s ? `${s.width}×${s.height}` : UNKNOWN,
    viewport: w ? `${w.innerWidth}×${w.innerHeight}` : UNKNOWN,
    pixelRatio: w?.devicePixelRatio ?? null,
    colorDepth: s?.colorDepth ?? null,
  };
}

/**
 * Count available media devices by kind. Client-side only — the same
 * navigator.mediaDevices.enumerateDevices() the app already uses, no socket.
 * Resolves to zeroed counts if the API is unavailable or denied.
 */
export async function getDeviceCounts() {
  const n = nav();
  const empty = { mic: 0, speaker: 0, webcam: 0 };
  if (!n?.mediaDevices?.enumerateDevices) return empty;
  try {
    const devices = await n.mediaDevices.enumerateDevices();
    return {
      mic: devices.filter((d) => d.kind === 'audioinput').length,
      speaker: devices.filter((d) => d.kind === 'audiooutput').length,
      webcam: devices.filter((d) => d.kind === 'videoinput').length,
    };
  } catch {
    return empty;
  }
}

/** Format a nullable value for display, applying an optional suffix. */
export function fmt(value, suffix = '') {
  if (value === null || value === undefined || value === '') return UNKNOWN;
  return `${value}${suffix}`;
}
