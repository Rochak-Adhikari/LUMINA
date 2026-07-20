# Frontend Roadmap

**Date:** 2026-07-20
Development phases for wiring the existing `src/Ui_TEST/` UI to the live backend.
The UI shell already exists; the work is integration + cleanup + polish, not
green-field.

## Phase 0 — Cleanup (prerequisite)

Remove dead references to removed backend features before new wiring:
- Delete emits `discover_kasa`, `discover_printers`.
- Delete listeners `cad_data`, `cad_status`, `cad_thought`.
- Remove `CadWindow` / `KasaWindow` / `PrinterWindow` imports + usage + files.

## Phase 1 — Backend Connection

- Central Socket.IO client (already a singleton in `AppTest.jsx`; consider
  extracting to `src/lib/socket.js`).
- REST client module (`src/lib/api.js`) with `http://localhost:8000` base.
- Connection-status indicator (`connection_status`, `model_status`, heartbeat).

## Phase 2 — Chat

- `user_input` emit; `chat_message` + `transcription` render.
- Streaming rendering, markdown, message history.

## Phase 3 — Voice

- Mic device selection, `start_audio`/`stop_audio`/`pause_audio`/`resume_audio`.
- `audio_data` playback + Visualizer amplitude.

## Phase 4 — Settings

- `get_settings`/`update_settings`, tool permissions.
- Browser-confirmation via REST (`/api/settings/browser-confirmation`).
- Persistence + synchronization with backend `SETTINGS`.

## Phase 5 — Tools

- `ToolsModule` execution/status/progress.
- Tool-confirmation gate (`tool_confirmation_request` → `confirm_tool`).

## Phase 6 — Browser

- Browser Workspace panel: `/local-browser/status`, `/local-browser/open`,
  `/api/vision/latest`, `browser_frame` stream.

## Phase 7 — Memory

- Memory viewer: `/memory/status`, `/memory/search`, `/memory/pending`,
  `/memory/confirm`, `/memory/deny`, `memory_lifecycle_event`, `memory_decision`.
- Project history / quests / events / archive CRUD (socket).

## Phase 8 — Polish

- Animations (framer-motion), loading states, responsiveness, error toasts.

See `DEVELOPMENT_PHASES.md` for per-phase tasks / files / checklists.
