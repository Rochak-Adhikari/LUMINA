// frontend/pages/Permissions/permissionsSchema.js
// Data-driven permission definitions. The Permissions Center renders entirely
// from this file. `settingKey` is the FUTURE binding into settings.json
// (tool_permissions.*) — stored now, NOT used for persistence this phase.
import {
  ShieldCheck, FolderCog, Monitor, Globe, Sparkles,
  LayoutGrid, Bot, Terminal, AlertTriangle,
} from 'lucide-react';

// Risk levels — drive the colored badge + overview counts.
export const RISK = {
  safe:         { id: 'safe',         label: 'Safe' },
  medium:       { id: 'medium',       label: 'Medium' },
  high:         { id: 'high',         label: 'High' },
  experimental: { id: 'experimental', label: 'Experimental' },
};

// Categories (left rail). `security` is a synthetic overview category.
export const PERMISSION_CATEGORIES = [
  { id: 'security',   label: 'Security Overview', icon: ShieldCheck,   overview: true },
  { id: 'filesystem', label: 'Filesystem',        icon: FolderCog },
  { id: 'desktop',    label: 'Desktop',           icon: Monitor },
  { id: 'browser',    label: 'Browser',           icon: Globe },
  { id: 'ai',         label: 'AI',                icon: Sparkles },
  { id: 'projects',   label: 'Projects',          icon: LayoutGrid },
  { id: 'automation', label: 'Automation',        icon: Bot },
  { id: 'developer',  label: 'Developer',         icon: Terminal },
  { id: 'danger',     label: 'Danger Zone',       icon: AlertTriangle, danger: true },
];

// Every permission. `disabled: true` marks placeholder/future capabilities that
// stay off and are not user-togglable yet.
export const PERMISSIONS = [
  // ── Filesystem ──────────────────────────────────────────────
  { category: 'filesystem', title: 'Read Files',        description: 'Allow Lumina to read files inside the active workspace.',        icon: FolderCog, risk: 'safe',   settingKey: 'tool_permissions.read_file',        defaultValue: false },
  { category: 'filesystem', title: 'Write Files',        description: 'Allow Lumina to create and overwrite workspace files.',          icon: FolderCog, risk: 'medium', settingKey: 'tool_permissions.write_file',       defaultValue: false },
  { category: 'filesystem', title: 'Read Directory',     description: 'Allow listing files and folders in the workspace.',              icon: FolderCog, risk: 'safe',   settingKey: 'tool_permissions.read_directory',   defaultValue: false },
  { category: 'filesystem', title: 'Create Directory',   description: 'Allow Lumina to create new folders.',                            icon: FolderCog, risk: 'medium', settingKey: 'tool_permissions.create_directory', defaultValue: false },
  { category: 'filesystem', title: 'File Controller',    description: 'Broader file operations (move, copy, delete) via the file tool.', icon: FolderCog, risk: 'high',   settingKey: 'tool_permissions.file_controller',  defaultValue: false },

  // ── Desktop ─────────────────────────────────────────────────
  { category: 'desktop', title: 'Desktop Control',   description: 'Control the desktop UI — clicks, keystrokes, window focus.',   icon: Monitor, risk: 'high',   settingKey: 'tool_permissions.desktop_control',   defaultValue: false },
  { category: 'desktop', title: 'Computer Control',  description: 'Low-level input control (mouse/keyboard automation).',        icon: Monitor, risk: 'high',   settingKey: 'tool_permissions.computer_control',  defaultValue: false },
  { category: 'desktop', title: 'Screen Process',    description: 'Capture and analyze the screen for context.',                icon: Monitor, risk: 'medium', settingKey: 'tool_permissions.screen_process',    defaultValue: false },
  { category: 'desktop', title: 'Open Applications', description: 'Launch desktop applications by name.',                        icon: Monitor, risk: 'medium', settingKey: 'tool_permissions.open_app',          defaultValue: true },
  { category: 'desktop', title: 'Computer Settings', description: 'Read and adjust OS-level settings (volume, brightness…).',    icon: Monitor, risk: 'high',   settingKey: 'tool_permissions.computer_settings', defaultValue: false },

  // ── Browser ─────────────────────────────────────────────────
  { category: 'browser', title: 'Browser Control',        description: 'Control the embedded Chromium browser via automation.',       icon: Globe, risk: 'medium', settingKey: 'tool_permissions.browser_control',        defaultValue: true },
  { category: 'browser', title: 'Local Browser',          description: 'Drive the local browser instance (navigation, actions).',     icon: Globe, risk: 'medium', settingKey: 'tool_permissions.local_browser_control',  defaultValue: true },
  { category: 'browser', title: 'Browser Agent',          description: 'Autonomous multi-step web tasks (headless agent).',           icon: Globe, risk: 'high',   settingKey: 'tool_permissions.browser_agent',          defaultValue: false },
  { category: 'browser', title: 'Browser Confirmation',   description: 'Require confirmation before sensitive browser actions.',      icon: Globe, risk: 'safe',   settingKey: 'settings.browser_confirmation_mode',      defaultValue: true },

  // ── AI ──────────────────────────────────────────────────────
  { category: 'ai', title: 'Web Search',       description: 'Search the web and summarize results.',            icon: Sparkles, risk: 'safe',         settingKey: 'tool_permissions.web_search',    defaultValue: true },
  { category: 'ai', title: 'Weather',          description: 'Fetch current weather for a location.',            icon: Sparkles, risk: 'safe',         settingKey: 'tool_permissions.weather',       defaultValue: true },
  { category: 'ai', title: 'YouTube',          description: 'Search and play videos in the embedded browser.',  icon: Sparkles, risk: 'safe',         settingKey: 'tool_permissions.youtube_play',  defaultValue: false },
  { category: 'ai', title: 'Future AI Skills', description: 'Reserved for dynamically created skills.',         icon: Sparkles, risk: 'experimental', settingKey: 'tool_permissions.future_ai',     defaultValue: false, disabled: true },

  // ── Projects ────────────────────────────────────────────────
  { category: 'projects', title: 'Create Project',       description: 'Create new project workspaces.',                    icon: LayoutGrid, risk: 'safe',   settingKey: 'tool_permissions.create_project',           defaultValue: false },
  { category: 'projects', title: 'Switch Project',       description: 'Switch the active project workspace.',              icon: LayoutGrid, risk: 'safe',   settingKey: 'tool_permissions.switch_project',           defaultValue: false },
  { category: 'projects', title: 'List Projects',        description: 'List all existing project workspaces.',             icon: LayoutGrid, risk: 'safe',   settingKey: 'tool_permissions.list_projects',            defaultValue: false },
  { category: 'projects', title: 'Workspace Activation', description: 'Follow project switches into workspace memory.',    icon: LayoutGrid, risk: 'safe',   settingKey: 'tool_permissions.workspace_activation_enabled', defaultValue: false },

  // ── Automation ──────────────────────────────────────────────
  { category: 'automation', title: 'System Reminder',  description: 'Schedule reminders and alarms.',              icon: Bot, risk: 'safe',         settingKey: 'tool_permissions.system_reminder', defaultValue: true },
  { category: 'automation', title: 'Send Message',     description: 'Send messages through connected channels.',    icon: Bot, risk: 'medium',       settingKey: 'tool_permissions.send_message',    defaultValue: true },
  { category: 'automation', title: 'Background Tasks',  description: 'Run long-lived background automations.',      icon: Bot, risk: 'experimental', settingKey: 'tool_permissions.background_tasks', defaultValue: false, disabled: true },

  // ── Developer ───────────────────────────────────────────────
  { category: 'developer', title: 'CMD Control',        description: 'Execute shell commands via the command tool.',       icon: Terminal, risk: 'high',         settingKey: 'tool_permissions.cmd_control',     defaultValue: true },
  { category: 'developer', title: 'Developer Console',  description: 'Access the in-app developer console + IPC inspector.', icon: Terminal, risk: 'medium',       settingKey: 'settings.developer_console',       defaultValue: false },
  { category: 'developer', title: 'Experimental APIs',  description: 'Enable unreleased/experimental capabilities.',        icon: Terminal, risk: 'experimental', settingKey: 'settings.experimental_apis',       defaultValue: false, disabled: true },

  // ── Danger Zone (all disabled placeholders) ─────────────────
  { category: 'danger', title: 'Registry Access',            description: 'Read/write the Windows registry.',                    icon: AlertTriangle, risk: 'experimental', settingKey: 'danger.registry_access',    defaultValue: false, disabled: true },
  { category: 'danger', title: 'PowerShell',                 description: 'Run arbitrary PowerShell scripts.',                   icon: AlertTriangle, risk: 'experimental', settingKey: 'danger.powershell',         defaultValue: false, disabled: true },
  { category: 'danger', title: 'Root Operations',            description: 'Elevated / administrator-level operations.',           icon: AlertTriangle, risk: 'experimental', settingKey: 'danger.root_operations',    defaultValue: false, disabled: true },
  { category: 'danger', title: 'Unsafe Commands',            description: 'Bypass command safety filters.',                      icon: AlertTriangle, risk: 'experimental', settingKey: 'danger.unsafe_commands',    defaultValue: false, disabled: true },
  { category: 'danger', title: 'Future Dangerous Features',  description: 'Reserved for high-risk capabilities.',                icon: AlertTriangle, risk: 'experimental', settingKey: 'danger.future',             defaultValue: false, disabled: true },
];

// Helpers ------------------------------------------------------------------
export const permissionsForCategory = (catId) =>
  PERMISSIONS.filter((p) => p.category === catId);

export const filterPermissions = (query) => {
  const q = (query || '').trim().toLowerCase();
  if (!q) return PERMISSIONS;
  return PERMISSIONS.filter((p) =>
    p.title.toLowerCase().includes(q) ||
    p.description.toLowerCase().includes(q) ||
    p.category.toLowerCase().includes(q) ||
    p.settingKey.toLowerCase().includes(q)
  );
};
