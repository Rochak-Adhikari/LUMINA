# UI Components

**Date:** 2026-07-20
Status legend: **Complete** / **Partial** / **Placeholder** / **Orphaned** (backend feature removed).

## Live layout (`src/Ui_TEST/`)

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| App shell | `AppTest.jsx` | Complete | Socket wiring, state, layout, overlays. |
| Sidebar | `components/Sidebar.jsx` | Complete | Panel switching. |
| Knowledge Archive panel | `panels/KnowledgeArchivePanel.jsx` | Partial | UI built; verify note CRUD sockets. |
| Events panel | `panels/EventsPanel.jsx` | Partial | UI built; verify event CRUD sockets. |
| Quests panel | `panels/QuestsPanel.jsx` | Partial | UI built; verify quest CRUD sockets. |
| System Settings panel | `panels/SystemSettingsPanel.jsx` | Partial | UI built; settings load/update. |
| Features panel | `panels/FeaturesPanel.jsx` | Partial | Feature catalog UI (605 lines). |
| Browser Workspace panel | `panels/BrowserWorkspacePanel.jsx` | Partial | Embedded browser control. |

## Reusable components (`src/components/`)

| Component | File | Status | Backend integration |
|-----------|------|--------|---------------------|
| Visualizer (orb) | `Visualizer.jsx` | Complete | `audio_data` amplitude. |
| Top Audio Bar | `TopAudioBar.jsx` | Complete | Audio/mic state. |
| Chat | `ChatModule.jsx` | Complete | `chat_message`, `user_input`. |
| Confirmation Popup | `ConfirmationPopup.jsx` | Complete | `tool_confirmation_request` / `confirm_tool`. |
| Browser Window | `BrowserWindow.jsx` | Complete | `browser_frame`, local-browser REST. |
| Memory Prompt | `MemoryPrompt.jsx` | Complete | `memory_lifecycle_event`, `memory_decision`. |
| Auth Lock | `AuthLock.jsx` | Complete | Face-auth socket events. |
| Tools Module | `ToolsModule.jsx` | Partial | Tool status/exec — needs verification. |
| Settings Window | `SettingsWindow.jsx` | Superseded | Replaced by `SystemSettingsPanel`. |
| **CAD Window** | `CadWindow.jsx` | **Orphaned** | Backend CAD removed — delete during integration. |
| **Kasa Window** | `KasaWindow.jsx` | **Orphaned** | Backend Kasa removed — delete. |
| **Printer Window** | `PrinterWindow.jsx` | **Orphaned** | Backend Printer removed — delete. |

## Canonical component checklist for integration

- Sidebar — Complete.
- Chat — Complete (verify streaming/history).
- Settings — Partial (needs backend integration verify).
- Voice — Complete (start/stop/pause/resume, playback).
- Status — Complete (connection/model status).
- Memory — Partial (viewer + lifecycle).
- Browser — Partial (control + state).
- Toolbar / Tools — Partial.
- CAD / Kasa / Printer — **Orphaned, remove.**
