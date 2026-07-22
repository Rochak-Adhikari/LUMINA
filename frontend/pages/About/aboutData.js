// frontend/pages/About/aboutData.js
// Static app identity + stack facts for the About page. Data-only, no view
// logic, no runtime lookups (versions are build-time constants from package.json;
// live runtime versions live in Diagnostics). No socket, no IPC, no backend.

export const APP = {
  name: 'Lumina',
  tagline: 'Local-first, voice-capable AI desktop assistant',
  version: '2.0.0',
  description:
    'Lumina is a private, local-first AI assistant. Voice and text conversation, long-term memory, browser control, file processing, and system automation — running on your own machine.',
};

// Core technology stack (build-time constants, mirrors package.json).
export const STACK = [
  { label: 'Electron', value: '43.1.1' },
  { label: 'React', value: '18.2.0' },
  { label: 'Vite', value: '5.1.0' },
  { label: 'Backend', value: 'FastAPI · Socket.IO' },
  { label: 'AI', value: 'Gemini Live' },
  { label: 'Memory', value: 'SQLite · FAISS · FTS5' },
];

// High-level capability pillars (summary; full catalog lives on the Skills page).
export const PILLARS = [
  { title: 'Voice & AI', text: 'Real-time voice conversation with VAD, streaming TTS, and a configurable persona engine.' },
  { title: 'Memory', text: 'Hybrid long-term memory that persists across restarts using keyword + semantic retrieval.' },
  { title: 'Automation', text: 'Browser control, file operations, and system automation gated behind explicit permissions.' },
  { title: 'Local-First', text: 'Runs on your machine. Face auth and processing stay local; no mandatory cloud account.' },
];

export const LINKS = [
  { label: 'Skills Catalog', page: 'skills' },
  { label: 'Permissions Center', page: 'permissions' },
  { label: 'Diagnostics', page: 'diagnostics' },
];
