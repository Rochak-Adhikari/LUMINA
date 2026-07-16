# Lumina V2 Contribution Guidelines

This document details the coding conventions, safety checks, and workflow rules for developers contributing to Lumina V2.

---

## 1. Coding Conventions

### A. DI Containment
- Always register new subsystems as contracts in `core/interfaces.py` first.
- Register factory creators inside `core/bootstrap.py` under the boot loader classes.
- Retrieve instances inside tool handlers or REST endpoints via `ServiceAccessor` or `RuntimeFacade` adapters. Never call container resolution inside lower layer classes directly.

### B. State Management
- Never mutate state outside `BrainState.transaction()` blocks.
- Do not store state flags as local attributes inside `server.py` or `lumina.py`. All active states (like confirmation statuses or timer thresholds) must belong to the central `BrainStateModel`.

### C. Wildcard Event Routing
- When introducing events, add a topic descriptor string to the events API list in `Docs/03_API/SOCKET_EVENTS.md`.
- Segment channels cleanly by dots (e.g. `session.started`, `tool.generate_cad.failure`).
- Guard subscriber routines from throwing unhandled exceptions to prevent EventBus execution loop crashes.

---

## 2. Pydantic Schema Guidelines

- All configuration fields in `settings.json` must map to `SettingsSchema` inside `backend/core/config_schema.py`.
- If custom parameters are added, define default validation thresholds and recovery floors (e.g. `Field(default=900, ge=350)`).
- Run syntax validations inside `load_settings()` to trigger auto-healing repairs on corrupted configs.

---

## 3. Pull Request Review Checklist

Prior to merging any technical proposal, verify the following:

- [ ] All code additions do not reference concrete `MemoryStore` or `ProjectManager` initializations.
- [ ] No circular imports exist between `core/` and `backend/server.py`.
- [ ] No print messages output raw VAD frames unless `DEBUG_AUDIO=1` is explicitly configured.
- [ ] All Socket.IO emitters contain validation try-except blocks and emit clean payload errors.
- [ ] Automated regression tests run successfully and return `7/7 PASS` results.
