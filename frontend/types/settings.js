// frontend/types/settings.js — settings shapes (JSDoc; JS project)

/**
 * @typedef {Object} SettingsSnapshot
 * @property {Object} tool_permissions
 * @property {boolean} persona_enabled
 * @property {string}  persona_mode
 * @property {number}  vad_min_speech_ms
 * @property {boolean} brain_core_enabled
 * @property {*}       [key: string]   // additional flat keys
 */

/**
 * @typedef {'idle'|'saving'|'saved'|'error'} SaveStatus
 */

/**
 * @typedef {Object} SettingsStoreState
 * @property {SettingsSnapshot} settings
 * @property {boolean} loaded
 * @property {boolean} dirty
 * @property {boolean} saving
 * @property {number|null} lastSaved
 * @property {string|null} error
 * @property {(path:string, fallback?:*) => *} get
 * @property {(path:string, value:*) => void} set
 * @property {() => Promise<void>} save
 * @property {() => Promise<void>} reload
 * @property {() => void} reset
 * @property {() => string} exportConfig
 * @property {(json:string) => boolean} importConfig
 */

export {};
