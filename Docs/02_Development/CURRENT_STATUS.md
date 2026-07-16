# Lumina V2 Current Status

This document defines the current release status, active development phase, and known technical debt of the Lumina V2 platform.

---

## 1. Release Metadata

- **Current Version**: 2.2.0 (Interface-first decoupled core)
- **Active Development Phase**: Post-Phase 4 (Stable Runtime Recovery completed)
- **Architectural Status**: Core platform is FROZEN
- **Last Updated**: July 2026

---

## 2. Completed Phases

All architectural foundational migrations are complete:

### Phase 1 — Runtime Foundation ✅
- Thread-safe dependency injection container.
- Transaction-managed Pydantic `BrainState` sandbox database.
- Topic-wildcard `InProcessEventBus` for local pub/sub.
- Sealed `RequestPipeline` execution middlewares.
- Central `RuntimeFacade` access layer.

### Phase 2 — Brain Runtime & State Migrations ✅
- State parameters (`pending_confirmation_id`) migrated to `BrainState`.
- Converted client Socket disconnect handlers to publish on `EventBus`.
- Wrapped `create_quest` parameters in structured `ExecutionContext` schemas.
- Decoupled `get_memories`, `generate_cad`, and `list_projects` to resolve via containerized interfaces (`IMemoryManager` and `IWorkspaceManager`).

### Phase 3 — Complete Architectural Migration ✅
- Introduced `SessionManager` to govern `AudioLoop` lifecycle variables.
- Introduced `ServiceAccessor` lookup bridge.
- Decoupled `server.py` from direct `AudioLoop` fields.
- Synchronized turn events with `BrainState.record_user_turn`.

### Phase 4 — Stable Runtime Recovery ✅
- **Milestone 4.1**: FastAPI dynamic port recovery scanner (checks port 8000 occupancy) and graceful shutdown publisher dispatch.
- **Milestone 4.2**: Instantiation inversion in `AudioLoop` (resolves database and workspace manager via facade).
- **Milestone 4.3**: Pydantic-based `SettingsSchema` configuration validator and self-healing.
- **Milestone 4.4**: Remote control paired dashboard command queues and phone stream audio chunks routed over EventBus.
- **Milestone 4.5**: Thread safety verification under concurrent stress, starvation, and heavily corrupted settings parameters.
- **Milestone 4.6**: Eliminated `_get_memory_store` legacy bypass path (all call-sites resolved via `_svc.memory_store`) and added `/debug/events` diagnostic endpoint.

---

## 3. Current & Next Phases

### Current Phase: Stable Maintenance
The system core is architecturally stable and frozen. All regression tests in `backend/brain/` pass cleanly.

### Next Phase: Phase 5 — Memory Engine (Planned)
- Implement SQLite `FTS5` full-text search.
- Integrate FAISS semantic vector search for concept matching.
- Implement access priority decay algorithms.

---

## 4. Known Technical Debt

1. **Global Module-Level States**: `server.py` contains several global variables (`last_user_activity`, `connected_clients`, `idle_disabled_until_ts`) mutated directly across async event tasks without locks.
2. **Lockless Logging**: `ProjectManager` writes chat logs to `chat_history.jsonl` using a simple `open()` without thread locks, risking lockups under rapid inputs.
3. **Duck-Typing Registrations**: `ProjectManager` and `MemoryStore` do not inherit from `IWorkspaceManager` and `IMemoryManager` directly; they are virtually mapped during startup bootstrap.
4. **`cv2` Import Spec**: Camera frames use `cv2.CAP_DSHOW` on Windows, but the MediaPipe landmark task relies on static asset placement (`face_landmarker.task`) which is currently hardcoded relative to the backend root.
