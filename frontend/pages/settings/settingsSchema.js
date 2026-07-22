// frontend/pages/settings/settingsSchema.js
// Declarative settings definition. `path` = the dot path in the settings store
// (single source: bind controls via useSetting(path)). `scale` maps UI units to
// stored units (e.g. slider 0–100 % → stored 0–1). NO persistence logic here.
import {
  Sliders, Bot, Mic, Brain, Globe, ShieldCheck, Palette, Terminal, Cog, MonitorSmartphone,
} from 'lucide-react';

export const SETTINGS_CATEGORIES = [
  {
    id: 'general', label: 'General', icon: Sliders,
    groups: [{
      title: 'Startup', items: [
        { key: 'launch_on_boot', path: 'launch_on_boot', title: 'Launch on system startup', description: 'Start Lumina when you log in', type: 'toggle' },
        { key: 'restore_session', path: 'restore_session', title: 'Restore last session', description: 'Reopen tabs and panels on launch', type: 'toggle' },
        { key: 'default_page', path: 'default_page', title: 'Default page', description: 'Page shown on launch', type: 'select', options: ['home', 'chat', 'browser'] },
      ],
    }],
  },
  {
    id: 'ai', label: 'AI', icon: Bot,
    groups: [{
      title: 'Model', items: [
        { key: 'persona_enabled', path: 'persona_enabled', title: 'Persona active', description: 'Enable Lumina personality', type: 'toggle' },
        { key: 'persona_mode', path: 'persona_mode', title: 'Persona mode', type: 'select', options: ['playful_mischievous_best_friend', 'calm_supportive', 'professional'] },
        { key: 'teasing_intensity', path: 'persona_teasing_intensity', title: 'Teasing intensity', type: 'slider', min: 0, max: 100, suffix: '%', scale: 100 },
      ],
    }],
  },
  {
    id: 'voice', label: 'Voice', icon: Mic,
    groups: [{
      title: 'Audio', items: [
        { key: 'vad_min_speech', path: 'vad_min_speech_ms', title: 'Min speech (ms)', type: 'slider', min: 100, max: 1000, suffix: 'ms' },
        { key: 'vad_silence', path: 'vad_silence_stop_ms', title: 'Silence stop (ms)', type: 'slider', min: 300, max: 2000, suffix: 'ms' },
        { key: 'continuous', path: 'continuous_conversation', title: 'Continuous conversation', type: 'toggle' },
      ],
    }],
  },
  {
    id: 'memory', label: 'Memory', icon: Brain,
    groups: [{
      title: 'Retrieval', items: [
        { key: 'real_embeddings', path: 'real_embeddings', title: 'Use real embeddings', description: 'gemini-embedding-001 (else local fallback)', type: 'toggle' },
        { key: 'top_k', path: 'memory_top_k', title: 'Retrieval top-K', type: 'slider', min: 1, max: 20, suffix: '' },
        { key: 'auto_capture', path: 'auto_capture_tasks', title: 'Auto-capture memories', type: 'toggle' },
      ],
    }],
  },
  {
    id: 'browser', label: 'Browser', icon: Globe,
    groups: [{
      title: 'Embedded Browser', items: [
        { key: 'restore_tabs', path: 'restore_tabs', title: 'Restore tabs on restart', type: 'toggle' },
        { key: 'confirmation_mode', path: 'browser_confirmation_mode', title: 'Confirmation mode', type: 'select', options: ['strict', 'relaxed', 'off'] },
        { key: 'block_external', path: 'keep_navigation_embedded', title: 'Keep navigation embedded', description: 'Never open external browser unless asked', type: 'toggle' },
      ],
    }],
  },
  {
    id: 'permissions', label: 'Permissions', icon: ShieldCheck,
    groups: [{
      title: 'Tool Access', items: [
        { key: 'web_search', path: 'tool_permissions.web_search', title: 'Web search', type: 'toggle' },
        { key: 'open_app', path: 'tool_permissions.open_app', title: 'Open applications', type: 'toggle' },
        { key: 'file_controller', path: 'tool_permissions.file_controller', title: 'File read/write', type: 'toggle' },
        { key: 'browser_control', path: 'tool_permissions.browser_control', title: 'Browser automation', type: 'toggle' },
      ],
    }],
  },
  {
    id: 'appearance', label: 'Appearance', icon: Palette,
    groups: [{
      title: 'Theme', items: [
        { key: 'accent', path: 'accent', title: 'Accent color', type: 'select', options: ['cyan', 'aqua', 'violet'] },
        { key: 'glass_intensity', path: 'glass_intensity', title: 'Glass blur', type: 'slider', min: 0, max: 60, suffix: 'px' },
        { key: 'reduce_motion', path: 'reduce_motion', title: 'Reduce motion', type: 'toggle' },
      ],
    }],
  },
  {
    id: 'developer', label: 'Developer', icon: Terminal,
    groups: [{
      title: 'Debug', items: [
        { key: 'brain_core', path: 'brain_core_enabled', title: 'Enable BrainCore', description: 'Route requests through cognitive layer', type: 'toggle' },
        { key: 'verbose_logs', path: 'verbose_logs', title: 'Verbose logging', type: 'toggle' },
        { key: 'devtools', path: 'devtools_autoopen', title: 'Auto-open DevTools', type: 'toggle' },
      ],
    }],
  },
  {
    id: 'system', label: 'System', icon: MonitorSmartphone, custom: 'system',
    groups: [],
  },
  {
    id: 'advanced', label: 'Advanced', icon: Cog,
    groups: [{
      title: 'Runtime', items: [
        { key: 'tool_clamp', path: 'tool_clamp_mode', title: 'Tool clamp mode', description: 'Restrict tools to an allowlist', type: 'select', options: ['on', 'off'] },
        { key: 'reconnect_backoff', path: 'reconnect_backoff_s', title: 'Reconnect backoff (s)', type: 'slider', min: 1, max: 30, suffix: 's' },
      ],
    }],
  },
];

export default SETTINGS_CATEGORIES;
