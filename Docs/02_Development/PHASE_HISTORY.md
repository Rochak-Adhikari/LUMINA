# Lumina V2 Phase History Specification

This document details the completed development phases, major changes, and validation suites of Lumina V2.

---

## 1. Timeline Overview

```mermaid
timeline
    title V2 Completed Milestones Timeline
    Phase 1 (July 2026) : DI Container Core : BrainState sandbox model : InProcessEventBus wildcard matches : RequestPipeline interceptors
    Phase 2 (July 2026) : State parameter migrations : Socket disconnect events : ExecutionContext wrappers : Subsystem decuplers
    Phase 3 (July 2026) : server.py decoupled : SessionManager loops : ServiceAccessor fallbacks : Heartbeat systems
    Phase 4 (July 2026) : FastAPI port conflicts : Config SettingsSchema validation & healing : Remote control EventBus integration : Legacy _get_memory_store retired
```

---

## 2. Completed Phase Details

### Phase 1 — Foundations (Phases 1.1 to 1.8)
- **Goal**: Establish the base dependency injection registry, transaction-managed state model, wildcard event bus, and request execution stack.
- **Major Changes**:
  - Created `DependencyContainer` for thread-safe bindings.
  - Implemented `BrainState` with Pydantic schemas, frozen `BrainSnapshot` copies, and rollback transactions.
  - Implemented `InProcessEventBus` for local pub/sub.
  - Created `RequestPipeline` interceptor and context models.
  - Defined abstract interfaces in `interfaces.py`.
- **Files Modified**:
  - `backend/core/container.py` [NEW]
  - `backend/core/interfaces.py` [NEW]
  - `backend/core/bootstrap.py` [NEW]
  - `backend/core/runtime_facade.py` [NEW]
  - `backend/brain/state.py` [NEW]
  - `backend/brain/events.py` [NEW]
  - `backend/core/pipeline.py` [NEW]
  - `backend/core/context.py` [NEW]
  - `backend/core/validation.py` [NEW]
- **Verification**: `test_phase_1_2.py` (21/21 PASS)

### Phase 2 — Brain Runtime & State Migrations (Phases 2.1 to 2.8)
- **Goal**: Transition execution boundaries from concrete global references to DI-resolved interfaces.
- **Major Changes**:
  - Migrated `pending_confirmation_id` to `BrainState` database managed by `RuntimeFacade`.
  - Converted socket client disconnect handlers to publish `session.disconnected` events on `EventBus`.
  - Wrapped `create_quest` calls in hierarchical `ExecutionContext` tokens and ran them through `RequestPipeline`.
  - Decoupled `get_memories`, `generate_cad`, `list_projects` and `AudioLoop` chat log writes to query DI interface handlers (`IMemoryManager` and `IWorkspaceManager`).
- **Files Modified**:
  - `backend/server.py`
  - `backend/lumina.py`
  - `backend/core/tool_handlers.py`
- **Verification**: `test_phase_2_1.py` through `test_phase_2_8.py` (26/26 PASS)

### Phase 3 — Complete Architectural Migration
- **Goal**: Decouple `server.py` from active `AudioLoop` fields and centralize service lifecycle lookups.
- **Major Changes**:
  - Created `SessionManager` to govern session attach/detach states and update connection timers.
  - Created `ServiceAccessor` bridge to lookup from container with passive fallback hooks.
  - Refactored `server.py` endpoints (quests, events, archive REST APIs) to resolve via `ServiceAccessor`.
- **Files Modified**:
  - `backend/core/session.py` [NEW]
  - `backend/core/service_accessor.py` [NEW]
  - `backend/server.py`
- **Verification**: `test_phase_3.py` (4/4 PASS)

### Phase 4 — Stable Runtime Recovery
- **Goal**: Stabilize server runtime, handle port conflicts, validate/heal config schemas, and eliminate legacy bypass paths.
- **Major Changes**:
  - Implemented `find_available_port()` in uvicorn main startup to scanner ports 8000–8009 automatically.
  - Added FastAPI shutdown handlers to publish `session.shutdown` event.
  - Resolved concrete `IMemoryManager` and `IWorkspaceManager` dependencies in `AudioLoop` constructor from DI.
  - Implemented `SettingsSchema` (Pydantic Settings model) and `validate_and_repair_settings()` self-healing logic.
  - Routed mobile paired dashboard endpoints (connection status, phone mic streams, and commands) to publish over EventBus.
  - **Milestone 4.6**: Eliminated legacy bypass `_get_memory_store()` function in `server.py`. Replaced all 15 call-sites with `_svc.memory_store`. Created `/debug/events` route. Created ARCHITECTURE.md.
- **Files Modified**:
  - `backend/server.py`
  - `backend/lumina.py`
  - `backend/core/bootstrap.py`
  - `backend/core/config_schema.py` [NEW]
  - `backend/dashboard_routes.py`
- **Verification**:
  - `test_phase_4_1.py` (2/2 PASS)
  - `test_phase_4_5.py` (3/3 PASS)
  - `test_phase_4_6.py` (7/7 PASS)
