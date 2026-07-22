// services/endpoints.js — backend contract constants (single source of truth)
// Backend base URL. Electron/backend hardcode localhost:8000 (see docs).
export const BASE_URL = 'http://localhost:8000';

// REST endpoints — mirror docs/backend/API_REFERENCE.md. Do not invent routes.
export const REST = {
  status: '/status',
  whatsappReply: '/whatsapp_reply',
  browserConfirmationGet: '/api/settings/browser-confirmation',
  browserConfirmationSet: '/api/settings/browser-confirmation',
  visionLatest: '/api/vision/latest',
  localBrowserStatus: '/local-browser/status',
  localBrowserOpen: '/local-browser/open',
  memoryStatus: '/memory/status',
  memorySearch: '/memory/search',
  memoryReindex: '/memory/reindex',
  memoryPending: '/memory/pending',
  memoryConfirm: '/memory/confirm',
  memoryDeny: '/memory/deny',
};

// Socket.IO events — mirror docs/backend/SOCKET_EVENTS.md.
// Outgoing (client -> server).
export const EMIT = {
  hbPong: 'hb_pong',
  startAudio: 'start_audio',
  stopAudio: 'stop_audio',
  pauseAudio: 'pause_audio',
  resumeAudio: 'resume_audio',
  confirmTool: 'confirm_tool',
  shutdown: 'shutdown',
  userInput: 'user_input',
  videoFrame: 'video_frame',
  saveMemory: 'save_memory',
  uploadMemory: 'upload_memory',
  processFile: 'process_file',
  promptWebAgent: 'prompt_web_agent',
  getSettings: 'get_settings',
  updateSettings: 'update_settings',
  revokeRemoteDevices: 'revoke_remote_devices',
  getToolPermissions: 'get_tool_permissions',
  updateToolPermissions: 'update_tool_permissions',
  killBrowserTools: 'kill_browser_tools',
  reminderAlarmDismissed: 'reminder_alarm_dismissed',
  memoryDecision: 'memory_decision',
  addMemory: 'add_memory',
  getMemories: 'get_memories',
  getMemoryStats: 'get_memory_stats',
};

// Incoming (server -> client).
export const ON = {
  hbPing: 'hb_ping',
  connectionStatus: 'connection_status',
  modelStatus: 'model_status',
  status: 'status',
  error: 'error',
  settings: 'settings',
  audioData: 'audio_data',
  transcription: 'transcription',
  chatMessage: 'chat_message',
  toolConfirmationRequest: 'tool_confirmation_request',
  projectUpdate: 'project_update',
  navigatePanel: 'navigate_panel',
  reminderAlarm: 'reminder_alarm',
  memoryLifecycleEvent: 'memory_lifecycle_event',
  browserFrame: 'browser_frame',
};
