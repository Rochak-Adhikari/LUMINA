# Project Checkpoint

**Date:** 2026-07-20
Permanent memory of where the project stands. This is the single source of truth
for resuming work without prior conversation context.

---

## Backend

- **Status:** COMPLETE · STABLE · FROZEN.
- **Completed work:** Phases 1–8 (runtime foundation → cognitive architecture →
  evolution → skill creator → skill runtime, all frozen). Phase 9.0 legacy
  cleanup: **Kasa, Printer, CAD removed**.
- **Registry counts:** SkillRegistry = **12**, Tier-1 (`ToolDispatcherRegistry`)
  = **9**, Tier-2 (`ACTION_REGISTRY`) = **18**, ServiceMetadataRegistry = **11**.
  Bijection `_TIER1_SKILLS == ToolDispatcherRegistry.keys()` (9==9) holds.
- **Test counts:** **913 passing** (Phase 5 + 6 + 7 + 8).
- **Runtime verification:** `Bootstrapper.bootstrap()` succeeds; DI resolves;
  imports clean; no dangling refs to removed modules.
- **Known issues:** none blocking. Intentional vestigial shims retained
  (`Bootstrapper(kasa_agent=None)`, AudioLoop `on_cad_*`/`on_device_update`
  params, `self.cad_agent=None`) — documented, harmless.

## Frontend

- **Status:** UI shell EXISTS, NOT integrated. React 18 + Vite + Electron +
  Three.js. Live UI = `src/Ui_TEST/AppTest.jsx` (re-exported by `src/App.jsx`).
  **No `frontend/` dir — frontend lives at repo root `src/`.**
- **Functional:** socket connection/heartbeat, audio session, text input,
  transcription/chat, tool-confirmation gate, panel navigation, reminder alarms,
  memory lifecycle events.
- **Remaining work:** integration cleanup (remove Kasa/Printer/CAD dead paths),
  then wire panels to live REST/Socket.IO (see `frontend/DEVELOPMENT_PHASES.md`).
- **Priority:** (1) Phase 0 cleanup of removed-feature references,
  (2) Phase 1 backend connection layer, (3) chat/voice, (4) settings/tools/
  browser/memory, (5) polish.

## Known integration gaps (must address)

1. `AppTest.jsx` emits `discover_kasa` / `discover_printers` — backend handlers
   removed. Remove.
2. `AppTest.jsx` listens for `cad_data` / `cad_status` / `cad_thought` — backend
   emits removed. Remove.
3. `CadWindow.jsx` / `KasaWindow.jsx` / `PrinterWindow.jsx` — orphaned components
   for removed backend features (`AppTest` still imports `CadWindow`). Delete.
4. No REST client module exists yet — add `src/lib/api.js` during Phase 1.
5. Tier-2 SkillSpec catalog covers only 3 of 18 actions (by design, not a bug) —
   do not treat as missing coverage.

## Current Development Focus

**Frontend integration.** Backend is frozen; do not modify unless integration
reveals a concrete bug.

## Next Session — the very next task

**Connect the frontend to the live backend: remove the removed-feature
placeholders (Kasa/Printer/CAD emits, listeners, and orphan components), then
replace placeholder UI data with real REST calls and Socket.IO wiring**, starting
with the backend-connection layer (Phase 1) per
`docs/frontend/DEVELOPMENT_PHASES.md`.

## Document index

- `docs/backend/` — BACKEND_STATUS, BACKEND_ARCHITECTURE, API_REFERENCE,
  SOCKET_EVENTS, TOOL_REGISTRY, CURRENT_BACKEND_STATE, NEXT_BACKEND_TASKS.
- `docs/frontend/` — FRONTEND_ROADMAP, FRONTEND_ARCHITECTURE, UI_COMPONENTS,
  API_INTEGRATION_PLAN, SOCKET_INTEGRATION_PLAN, CURRENT_FRONTEND_STATE,
  DEVELOPMENT_PHASES.
- `docs/PROJECT_CHECKPOINT.md` — this file.
