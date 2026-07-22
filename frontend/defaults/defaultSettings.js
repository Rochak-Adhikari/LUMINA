// frontend/defaults/defaultSettings.js
// Canonical default configuration (mirrors backend settings.json shape).
// Single source for "Reset to Defaults" — never hardcode defaults in components.
// Persisted via SettingsService → SettingsIPC (Socket.IO get_settings/update_settings).

export const DEFAULT_SETTINGS = {
  // ── Tool permissions (nested) ─────────────────────────────
  tool_permissions: {
    workspace_activation_enabled: false,
    read_file: false,
    write_file: false,
    read_directory: false,
    create_directory: false,
    create_project: false,
    switch_project: false,
    list_projects: false,
    file_controller: false,
    desktop_control: false,
    computer_control: false,
    computer_settings: false,
    screen_process: false,
    open_app: true,
    browser_control: true,
    local_browser_control: true,
    browser_agent: false,
    web_search: true,
    weather: true,
    youtube_play: false,
    system_reminder: true,
    send_message: true,
    cmd_control: true,
    background_tasks: false,
    future_ai: false,
  },

  // ── AI / persona ──────────────────────────────────────────
  persona_enabled: true,
  persona_mode: 'professional',
  persona_teasing_intensity: 0.6,
  persona_idle_enabled: true,
  persona_strict_sensitivity: 0.5,
  persona_adaptive_mode: true,

  // ── Voice ─────────────────────────────────────────────────
  vad_min_speech_ms: 350,
  vad_silence_stop_ms: 900,
  continuous_conversation: false,

  // ── Memory ────────────────────────────────────────────────
  real_embeddings: true,
  memory_top_k: 8,
  auto_capture_tasks: true,

  // ── Browser ───────────────────────────────────────────────
  browser_confirmation_mode: 'relaxed',
  restore_tabs: true,
  keep_navigation_embedded: true,

  // ── General ───────────────────────────────────────────────
  launch_on_boot: false,
  restore_session: true,
  default_page: 'home',

  // ── Appearance ────────────────────────────────────────────
  accent: 'cyan',
  glass_intensity: 30,
  reduce_motion: false,

  // ── Developer / advanced ─────────────────────────────────
  brain_core_enabled: false,
  verbose_logs: false,
  developer_console: false,
  experimental_apis: false,
  devtools_autoopen: false,
  tool_clamp_mode: 'off',
  reconnect_backoff_s: 8,

  // ── Security ──────────────────────────────────────────────
  face_auth_enabled: false,
  camera_flipped: false,

  // ── Devices (selected media device ids; persisted locally) ─
  selected_mic_id: '',
  selected_speaker_id: '',
  selected_webcam_id: '',

  // ── Layout (resizable column widths, px; center is the flexible remainder) ─
  layout_sidebar_w: 220,
  layout_chat_w: 380,
};

// Deep clone so callers never mutate the shared default object.
export const cloneDefaults = () => JSON.parse(JSON.stringify(DEFAULT_SETTINGS));

export default DEFAULT_SETTINGS;
