// frontend/services/endpoints.js — backend contract constants (frontend mirror).
// Mirrors src/services/endpoints.js so the new frontend never imports from the
// legacy tree. Single source of truth for BASE_URL + Socket.IO event names.
export const BASE_URL = 'http://localhost:8000';

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

  // Workspace CRUD (quests / events / archive notes).
  listQuests: 'list_quests',
  createQuest: 'create_quest',
  updateQuest: 'update_quest',
  deleteQuest: 'delete_quest',
  listEvents: 'list_events',
  createEvent: 'create_event',
  updateEvent: 'update_event',
  deleteEvent: 'delete_event',
  listArchiveNotes: 'list_archive_notes',
  createArchiveNote: 'create_archive_note',
  updateArchiveNote: 'update_archive_note',
  deleteArchiveNote: 'delete_archive_note',
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
  workspaceOpen: 'workspace_open',

  // Workspace CRUD responses.
  questsList: 'quests_list',
  questCreated: 'quest_created',
  questUpdated: 'quest_updated',
  questDeleted: 'quest_deleted',
  eventsList: 'events_list',
  eventCreated: 'event_created',
  eventUpdated: 'event_updated',
  eventDeleted: 'event_deleted',
  archiveNotesList: 'archive_notes_list',
  archiveNoteCreated: 'archive_note_created',
  archiveNoteUpdated: 'archive_note_updated',
  archiveNoteDeleted: 'archive_note_deleted',
  panelError: 'panel_error',

  // Memory responses.
  memories: 'memories',
  memoryStats: 'memory_stats',
  memoryAdded: 'memory_added',
};
