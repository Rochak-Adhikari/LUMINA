# Frontend Architecture

**Date:** 2026-07-20
Descriptive snapshot of `src/`. Do not modify.

## Folder structure

```
/ (repo root)
├── index.html              # Vite entry
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── package.json            # React/Vite/Electron/Three deps
├── electron/main.js        # Electron main process (frameless window, CDP :9223, download mgr, spawns backend)
└── src/
    ├── main.jsx            # React root
    ├── App.jsx             # re-exports Ui_TEST/AppTest (live UI)
    ├── App_original_backup.jsx, App.jsx.bak   # retained backups
    ├── index.css
    ├── components/         # reusable widgets (see UI_COMPONENTS.md)
    └── Ui_TEST/
        ├── AppTest.jsx     # live app shell (683 lines) — socket, state, layout
        ├── main_test.jsx   # alt test entry
        ├── components/Sidebar.jsx
        └── panels/         # Knowledge Archive, Events, Quests, SystemSettings, Features, BrowserWorkspace
```

## Layouts

- Single frameless Electron window (custom title bar), dark background.
- `AppTest.jsx` renders: left `Sidebar` → active panel (center) → orb
  `Visualizer` + `TopAudioBar` + chat + overlays (`ConfirmationPopup`,
  `MemoryPrompt`, reminder alarm).
- Panel switching via `activePanel` state (`home | archive | events | quests |
  settings | features | browser`).

## Shared components

`Visualizer` (Three.js orb), `TopAudioBar`, `ChatModule`, `ConfirmationPopup`,
`BrowserWindow`, `MemoryPrompt`, `AuthLock`, `ToolsModule`. (Orphaned:
`CadWindow`, `KasaWindow`, `PrinterWindow` — removed backend features.)

## Providers / hooks / state

- **No** dedicated context providers or custom hooks directory. State is local
  to `AppTest.jsx` via `useState`/`useRef`/`useEffect` (React built-ins).
- A **module-level singleton** `const socket = io('http://localhost:8000')` in
  `AppTest.jsx` is the single Socket.IO connection; components receive data via
  props/state from `AppTest`.
- No Redux/Zustand/Context — state management is component-local.

## Routing

- No router library. Navigation is `activePanel` state + `setActivePanel`
  (also driven by backend `navigate_panel` socket event).

## Electron main (`electron/main.js`)

- Frameless 1920×1080 window, `nodeIntegration: true`, `contextIsolation: false`.
- ANGLE d3d11 + Vulkan GPU switches; CDP `remote-debugging-port 9223` (backend
  Playwright connects to internal tabs).
- Spawns the Python backend; discovers recovered port 8000–8009; native download
  manager; `BrowserView` tab management for embedded browser.

## Backend connection contract

- REST + Socket.IO both hardcode `http://localhost:8000`.
- No API-client abstraction yet — direct `socket.emit`/`socket.on` and (to be
  added) `fetch` calls. See `API_INTEGRATION_PLAN.md` / `SOCKET_INTEGRATION_PLAN.md`.
