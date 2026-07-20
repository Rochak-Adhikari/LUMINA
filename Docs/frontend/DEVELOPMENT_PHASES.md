# Development Phases (Frontend Integration)

**Date:** 2026-07-20
Detailed per-phase plan. Files listed are the primary surfaces; new files marked
(new). Backend is frozen — do not modify it unless a phase surfaces a real bug.

---

## Phase 0 — Cleanup

- **Goal:** Remove dead references to removed backend features (Kasa/Printer/CAD).
- **Tasks:** delete `discover_kasa`/`discover_printers` emits; delete
  `cad_data`/`cad_status`/`cad_thought` listeners; remove `CadWindow`/`KasaWindow`/
  `PrinterWindow` imports, usages, and files.
- **Files:** `src/Ui_TEST/AppTest.jsx`, `src/components/CadWindow.jsx`,
  `KasaWindow.jsx`, `PrinterWindow.jsx`.
- **Expected:** No dead socket paths; UI builds clean.
- **Checklist:** [ ] emits removed [ ] listeners removed [ ] orphan components
  deleted [ ] app boots with no console errors for missing events.

## Phase 1 — Backend Connection

- **Goal:** One reliable REST + Socket.IO layer with visible connection state.
- **Tasks:** extract socket singleton → `src/lib/socket.js` (new); add
  `src/lib/api.js` (new) fetch wrapper; wire connection/model status UI.
- **Files:** `src/lib/socket.js` (new), `src/lib/api.js` (new), `AppTest.jsx`.
- **Expected:** `GET /status` OK; live `connection_status`/`model_status`.
- **Checklist:** [ ] api client [ ] socket module [ ] status indicator [ ] reconnect handling.

## Phase 2 — Chat

- **Goal:** Real conversation flow.
- **Tasks:** `user_input` emit; render `chat_message` + `transcription`; history;
  markdown; streaming append.
- **Files:** `ChatModule.jsx`, `AppTest.jsx`.
- **Expected:** Typed + spoken turns render correctly.
- **Checklist:** [ ] send [ ] receive [ ] markdown [ ] history [ ] streaming.

## Phase 3 — Voice

- **Goal:** Full audio loop.
- **Tasks:** device select; `start/stop/pause/resume_audio`; `audio_data`
  playback; Visualizer amplitude.
- **Files:** `TopAudioBar.jsx`, `Visualizer.jsx`, `AppTest.jsx`.
- **Expected:** Speak → transcription → AI audio playback + orb reacts.
- **Checklist:** [ ] mic start/stop [ ] mute [ ] playback [ ] visualizer.

## Phase 4 — Settings

- **Goal:** Persistent, synchronized settings.
- **Tasks:** `get_settings`/`update_settings`; tool permissions;
  browser-confirmation REST.
- **Files:** `SystemSettingsPanel.jsx`, `AppTest.jsx`.
- **Expected:** Changes persist across restart; backend `SETTINGS` in sync.
- **Checklist:** [ ] load [ ] save [ ] permissions [ ] browser mode.

## Phase 5 — Tools

- **Goal:** Tool execution UX.
- **Tasks:** `ToolsModule` status/progress; confirmation gate.
- **Files:** `ToolsModule.jsx`, `ConfirmationPopup.jsx`, `AppTest.jsx`.
- **Expected:** Gated tools prompt; results shown.
- **Checklist:** [ ] status [ ] progress [ ] confirm/deny.

## Phase 6 — Browser

- **Goal:** Embedded browser control + state.
- **Tasks:** `/local-browser/status`, `/local-browser/open`, `/api/vision/latest`,
  `browser_frame`.
- **Files:** `BrowserWorkspacePanel.jsx`, `BrowserWindow.jsx`.
- **Expected:** Open URL, see frames, read tab state.
- **Checklist:** [ ] status [ ] open [ ] frame stream [ ] controls.

## Phase 7 — Memory

- **Goal:** Memory viewer + project history.
- **Tasks:** memory REST (`status`/`search`/`pending`/`confirm`/`deny`);
  `memory_lifecycle_event`/`memory_decision`; quests/events/archive CRUD (socket).
- **Files:** `MemoryPrompt.jsx`, `KnowledgeArchivePanel.jsx`, `EventsPanel.jsx`,
  `QuestsPanel.jsx`, `AppTest.jsx`.
- **Expected:** Browse/search/confirm memories; CRUD panels work.
- **Checklist:** [ ] status [ ] search [ ] pending confirm/deny [ ] CRUD.

## Phase 8 — Polish

- **Goal:** Production feel.
- **Tasks:** framer-motion transitions; loading/empty/error states; responsive
  layout; toasts.
- **Files:** all panels/components.
- **Expected:** Smooth, resilient UI.
- **Checklist:** [ ] animations [ ] loading [ ] errors [ ] responsive.
