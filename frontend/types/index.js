// frontend/types/index.js — shared shape definitions (JSDoc; JS project, no TS)

/**
 * @typedef {Object} RouteDef
 * @property {string} id
 * @property {string} label
 * @property {Function} icon        lucide-react icon component
 * @property {Function} component   page component
 * @property {'main'|'util'} group
 */

/**
 * @typedef {Object} SettingItem
 * @property {string} key
 * @property {string} title
 * @property {string} [description]
 * @property {'toggle'|'slider'|'select'|'text'} type
 * @property {*} [value]
 */

export {};
