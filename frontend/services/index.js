// frontend/services/index.js — service layer barrel
export { BASE_URL, EMIT, ON } from './endpoints';
export { socket } from './socketClient';
export {
  subscribe, emit, isConnected,
  subscribeStatus, getStatus,
} from './socketManager';
export { isElectron } from './ipcClient';
export {
  subscribe as ipcSubscribe,
  unsubscribe as ipcUnsubscribe,
  invoke as ipcInvoke,
  send as ipcSend,
} from './ipcManager';
