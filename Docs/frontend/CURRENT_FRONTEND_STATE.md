# Current Frontend State

**Date:** 2026-07-20
Inspected from `src/` (repo root; there is **no** `frontend/` directory). Do not
modify — this is a snapshot of what exists.

## Framework / stack

- **React 18** + **Vite 5**, packaged in **Electron 28** (`electron/main.js`).
- **Three.js** + `@react-three/fiber` + `drei` (orb/visualizer).
- **framer-motion**, **lucide-react**, **tailwindcss**, `clsx`/`tailwind-merge`.
- **socket.io-client 4** — realtime to backend `http://localhost:8000`.
- Entry: `index.html` → `src/main.jsx` → `src/App.jsx`.

## Active entry point

`src/App.jsx` re-exports `src/Ui_TEST/AppTest.jsx` — **the live UI is the
`Ui_TEST/` layout**, not the components directly under `src/components/`. The
production `App_original_backup.jsx` / `App.jsx.bak` are retained backups.

## Pages / panels (live, `src/Ui_TEST/`)

| Panel | File | Status |
|-------|------|--------|
| Home (orb + chat + audio) | `AppTest.jsx` (683 lines) | Functional shell; socket-wired |
| Sidebar | `components/Sidebar.jsx` | Functional (panel switching) |
| Knowledge Archive | `panels/KnowledgeArchivePanel.jsx` | UI built; socket-wired |
| Events | `panels/EventsPanel.jsx` | UI built; socket-wired |
| Quests | `panels/QuestsPanel.jsx` | UI built; socket-wired |
| System Settings | `panels/SystemSettingsPanel.jsx` | UI built; socket-wired |
| Features | `panels/FeaturesPanel.jsx` | UI built |
| Browser Workspace | `panels/BrowserWorkspacePanel.jsx` | UI built; socket-wired |

## Reusable components (`src/components/`)

| Component | Status |
|-----------|--------|
| `Visualizer.jsx` (Three.js orb) | Functional |
| `TopAudioBar.jsx` | Functional |
| `ChatModule.jsx` | Functional |
| `ConfirmationPopup.jsx` | Functional (tool-confirmation gate) |
| `BrowserWindow.jsx` | Functional |
| `MemoryPrompt.jsx` | Functional |
| `AuthLock.jsx` | Functional (face-auth lock) |
| `ToolsModule.jsx` | Partial |
| `SettingsWindow.jsx` (481 lines) | Superseded by `SystemSettingsPanel` |
| `CadWindow.jsx` | **ORPHANED — backend CAD removed** |
| `KasaWindow.jsx` | **ORPHANED — backend Kasa removed** |
| `PrinterWindow.jsx` | **ORPHANED — backend Printer removed** |

## What is functional

- Socket.IO connection + heartbeat, connection/model status.
- Audio session start/stop/pause/resume, AI audio playback.
- Text input (`user_input`), transcription + chat rendering.
- Tool-confirmation gate (`tool_confirmation_request` → `confirm_tool`).
- Panel navigation (voice `navigate_panel` + manual).
- Settings load, project update, reminder alarms, memory lifecycle events.

## What is placeholder / needs work

- `ToolsModule` — partial.
- Panels render UI but data flows need verification against live REST/socket.

## Needs backend integration / cleanup (GAPS)

- `AppTest.jsx` still **emits** `discover_kasa`, `discover_printers` and
  **listens** for `cad_data`, `cad_status`, `cad_thought` — all removed from the
  backend. Silent no-ops; must be removed during integration.
- `CadWindow.jsx`, `KasaWindow.jsx`, `PrinterWindow.jsx` — orphaned components for
  removed backend features. `AppTest.jsx` still imports `CadWindow`. Remove during
  integration.
