# Lumina - Current Status Specification

## Project Overview
Lumina is a local-first, voice-first intelligent operating system and conversational companion designed to run directly on the user's desktop. Rather than operating as a simple text-based chatbot or corporate assistant, Lumina is structured as a resilient, extensible reasoning engine. The core engine manages memory lifecycle, context assembly, and tool routing, while capabilities expand dynamically via modular, sandboxed skills.

> [!IMPORTANT]
> The repository has recently been cleaned and reorganized to separate core code from tests, experiments, utility tools, and documentation. The directory [Docs/TRUTH/](file:///E:/AI/LUMINA/Docs/TRUTH/) is now the project's single source of truth for architecture plans, specifications, and development rules. All historical and obsolete specifications have been relocated to [Docs/Archive/](file:///E:/AI/LUMINA/Docs/Archive/) for traceability.

---

## Repository Organization
The repository has been structured into clean, isolated layers to protect core application code from testing helpers and developer experiments:

*   **[backend/](file:///E:/AI/LUMINA/backend/)**: Core Python application code including agents (CAD, printer, Kasa, web, authenticator), state management, and server endpoints.
    *   **[backend/core/](file:///E:/AI/LUMINA/backend/core/)**: Dependency injection container, bootstrapping routines, context factory, and pipeline.
    *   **[backend/brain/](file:///E:/AI/LUMINA/backend/brain/)**: Event bus, memory models, and state transactions.
    *   **[backend/tests/](file:///E:/AI/LUMINA/backend/tests/)**: Reorganized suite containing all unit tests, integration tests, and verification scripts.
*   **[frontend/](file:///E:/AI/LUMINA/frontend/)**: React-based UI assets and components.
*   **[electron/](file:///E:/AI/LUMINA/electron/)**: Electron main process orchestration and system integration window.
*   **[experiments/](file:///E:/AI/LUMINA/experiments/)**: Standalone prototypes, proof-of-concept scripts, and temporary demos (e.g., gesture control tests).
*   **[tools/](file:///E:/AI/LUMINA/tools/)**: Standalone maintenance, logging diagnostics, search helpers, and database repair utilities.
*   **[Docs/](file:///E:/AI/LUMINA/Docs/)**: Separated into structured architectural, API, and guide subdirectories.
    *   **[Docs/TRUTH/](file:///E:/AI/LUMINA/Docs/TRUTH/)**: authoritative specification schemas, development regulations, and roadmaps.
    *   **[Docs/Archive/](file:///E:/AI/LUMINA/Docs/Archive/)**: Historical planning drafts and phase summaries.

---

## Current Architecture
The backend application follows a clean, decoupled dependency-injected design:
1.  **Dependency Injection (DI) Container**: Services are registered dynamically via `container.py` and resolved using accessor helpers to prevent tight import coupling.
2.  **State Sandbox (BrainState)**: Enforces thread-safe, transaction-driven updates to session records and settings. Snapshots returned are read-only and immutable.
3.  **In-Process Event Bus**: Pub/sub messaging engine decoupling upstream endpoints from long-running agent threads.
4.  **Request Execution Pipeline**: Decoupled handlers process user voice/text requests in serial middleware steps (validation, logging, pre-processing, execution, post-processing).
5.  **Runtime Facade**: Unified entrance interface for starting/stopping background threads, managing memory layers, and handling cleanup.

---

## Current Implementation Status

| Stage / Phase | Focus | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Runtime Foundation | ✅ Completed | Dependency Injection container (`core/container.py`), Application bootstrapper (`core/bootstrap.py`), Lifecycle hosting (`core/application.py`), and Context mapping (`core/context.py`) are implemented and verified via unit tests. |
| **Phase 2** | Brain Architecture | 🟡 Partially Complete | The sandbox state class (`brain/state.py`) and pub/sub event bus (`brain/events.py`) are implemented and tested. Integration with active server routes is ongoing as legacy patterns are eliminated. |
| **Phase 3** | Interface Refactor & Clean Architecture | ✅ Completed | The `SessionManager` (`core/session.py`) and `ServiceAccessor` (`core/service_accessor.py`) interfaces are fully implemented and integrated. All backend execution paths route through these abstractions. |
| **Phase 4** | **Stable Runtime Recovery** | ✅ **COMPLETED** | **All milestones complete (2026-07-17)**. Milestones 4.1-4.3 (port recovery, AudioLoop DI, SessionManager wiring), 4.4 (DI finalization), and 4.5 (unified lifecycle) are complete. All legacy fallback patterns eliminated. Single-owner DI architecture achieved. |
| **Phase 5** | Memory Engine | ❌ Not Started | **Next Phase**. Focuses on semantic memory storage, local vector search indexes, knowledge graph structures, and project/workspace context maps. |
| **Phase 6** | Planning Engine | ❌ Not Started | Planned future phase. Focuses on structured task decomposition, reasoning chains, dynamic tool binding, and adaptive execution planners. |

---

## Current Technical Debt

**Phase 4 debt: ✅ ALL RESOLVED (2026-07-17)**

*   ~~**Multiple MemoryStore Instances**~~ ✅ *Resolved (Milestone 4.4)*: Single MemoryStore registered eagerly in `Bootstrapper.bootstrap()`. The `_fallback_memory_store` global and `_get_memory_store()` fallback are deleted; all CRUD endpoints resolve via `_svc.memory_store`. MemoryEngine is a DI lazy singleton (`IKnowledgeManager`), no duplicate construction.
*   ~~**AudioLoop Constructs Dependencies Inline**~~ ✅ *Resolved (Milestone 4.2)*: `AudioLoop.__init__` accepts injected `MemoryStore`/`ProjectManager`; DI resolution always succeeds post-4.4 since Bootstrapper registers both eagerly.
*   ~~**Remaining server.py Globals**~~ ✅ *Resolved (Milestone 4.3)*: `audio_loop`, `loop_task`, `authenticator` owned by DI-registered `SessionManager`. `kasa_agent` deliberately remains a DI-managed `ISmartHomeAgent` singleton.
*   ~~**Port Recovery**~~ ✅ *Resolved (Milestone 4.1)*: 8000 kept when free; 8001–8009 scan only when occupied.
*   ~~**Legacy Shutdown Path**~~ ✅ *Resolved (Milestone 4.5)*: All three shutdown paths (`shutdown_event`, frontend `shutdown` socket, `stop_audio`) delegate to `ApplicationHost.stop()`, which runs `_unified_shutdown()` via LIFO cleanup hooks with error isolation.

**Deferred (non-blocking, tracked for future phases):**

*   **Tests Not Fully Consolidated**: Phase tests remain in `backend/core/` and `backend/brain/` (excluded from `pytest.ini testpaths`); runnable individually via `python <file>`. Consolidation deferred — pytest is still not installed in the lumina env, which blocks a unified runner.
*   **server.py size** (~3,400 lines): modularization deferred to Phase 5 when BrainCore routing gives handlers a natural new home.
*   **AudioLoop loop_task lifecycle**: task reference owned by SessionManager; ApplicationHost stops it via the unified hook. Full AudioLoop lifecycle ownership by ApplicationHost deferred to Phase 5.

---

## Phase 4 Implementation Plan

The objective of Phase 4 is to eliminate the technical debt identified above, stabilize startup/shutdown lifecycles, complete dependency injection, and achieve clean architecture alignment.

### Milestone 4.1: Graceful Startup, Port Recovery & Logging ✅ Complete
*   **Objective**: Implement a self-healing port recovery system to handle socket starvation, and improve system startup logs.
*   **Files changed**: `backend/server.py` (module-scope `is_port_free` / `select_startup_port` helpers + `__main__` entrypoint), `backend/tests/test_port_recovery.py` (new regression test).
*   **Delivered**: Port 8000 is preserved when free; only when occupied does startup scan 8001–8009 for the first free port. Descriptive `[STARTUP]` console output on free/occupied/recovered/failure. Range exhaustion raises an explicit `OSError` instead of an opaque uvicorn bind crash. The probe intentionally omits `SO_REUSEADDR` so it matches uvicorn's real bind on Windows.
*   **Verification**: 6/6 regression tests pass (stdlib `unittest`). Live probe confirmed: 8000 free → binds 8000; 8000 occupied → recovers to 8001.
*   **Note**: Electron (`electron/main.js`) dynamically discovers the recovered backend port via stdout parsing or sequential status scanning on ports 8000-8009 and redirects port 8000 traffic using `session.defaultSession.webRequest.onBeforeRequest` (Milestone 4.1.1).
*   **Dependencies**: Phase 1 container setup.

### Milestone 4.2: Dependency Injection for AudioLoop ✅ Complete
*   **Objective**: Refactor `AudioLoop` initialization to receive its `MemoryStore` and `ProjectManager` dependencies dynamically via dependency injection, resolving inline constructor instantiation.
*   **Files changed**: `backend/lumina.py`, `backend/core/bootstrap.py`, `backend/server.py`, `backend/tests/test_phase_4_2.py`
*   **Delivered**: `AudioLoop` constructor refactored to accept optional `memory_store` and `project_manager` parameters with a fallback resolution chain (args -> DI container -> inline). `bootstrap.py` registers `MemoryStore` and `ProjectManager` in the container. `server.py` resolves and passes them.
*   **Verification**: Dedicated regression suite `backend/tests/test_phase_4_2.py` (3/3 pass: constructor injection, DI-container resolution, inline fallback). Architecture test `core/test_phase_1_8.py` updated for the canonical 10-service registry, including explicit Phase 4.2 metadata checks (all pass). Phase suites `core/test_phase_1_4`–`1_7` and `brain/test_phase_2_1` pass; `backend/tests/test_port_recovery` 6/6 pass. Pytest-based suites in `backend/tests/` remain unexecuted (pytest not installed in the lumina env).
*   **Dependencies**: Phase 1 container setup.

### Milestone 4.3: Decouple Global State & Wire SessionManager ✅ Complete
*   **Objective**: Eradicate the scattered global variables (`audio_loop`, `loop_task`, `authenticator`) inside `server.py` by fully routing loop lifecycle and state queries through `SessionManager`.
*   **Files changed**: `backend/core/session.py` (SessionManager now owns `loop_task` and `authenticator` via `set_loop_task`/`set_authenticator` + properties; `get_status()` extended), `backend/server.py` (module globals removed; every handler reads via `_session_mgr`), `backend/tests/test_phase_4_3.py` (new regression test).
*   **Delivered**: `audio_loop`, `loop_task`, and `authenticator` are owned exclusively by the DI-registered `SessionManager`. Zero `global` statements for these names remain; all handler reads bind locally from `_session_mgr` (AST-verified). Lifecycle order preserved: detach clears only the session reference — task cancellation stays an explicit shutdown action. `kasa_agent` intentionally remains a DI-managed `ISmartHomeAgent` singleton (service lifetime, not session lifetime — per approved scope).
*   **Verification**: `test_phase_4_3` 6/6 pass; `test_phase_4_2` 3/3; `test_port_recovery` 6/6; phase suites `core/test_phase_1_4`–`1_8`, `brain/test_phase_2_1`, `brain/test_phase_3` all pass. Live smoke: single bootstrap, `/status` 200, zero errors.
*   **Dependencies**: Milestone 4.2.

### Milestone 4.4: Authoritative ServiceAccessor Integration ✅ Complete
*   **Objective**: Clean up legacy lookup functions (like `_get_memory_store()`) and route all CRUD endpoint queries exclusively through the DI-resolved `ServiceAccessor` (`_svc.memory_store`).
*   **Files changed**: `backend/server.py` (16 `_get_memory_store()` call sites → `_svc.memory_store`; `memory_engine` global removed → `_svc.knowledge_manager`; legacy `container.override()` block removed from `start_audio`), `backend/core/bootstrap.py` (MemoryEngine registered as lazy DI singleton `IKnowledgeManager`), `backend/tests/test_phase_4_4.py` (new regression suite).
*   **Delivered**: `_get_memory_store()` and `_fallback_memory_store` deleted. All memory/CRUD lookups route through `_svc`. Single MemoryStore instance (registered eagerly in Bootstrapper); MemoryEngine lazy singleton (embedding-probe deferred to first use). ServiceMetadataRegistry now describes 11 services.
*   **Verification**: `tests/test_phase_4_4.py` — 9 tests: singleton uniqueness (MemoryStore, ProjectManager), no-duplicate-store, ServiceAccessor resolution + flags, AST check that `_get_memory_store`/`_fallback_memory_store` are gone. 8 pass, 1 skipped (MemoryEngine singleton — requires numpy, unavailable in test interpreter; validated at runtime).
*   **Dependencies**: Milestone 4.3.

### Milestone 4.5: Unified Lifecycle & Clean Shutdown ✅ Complete
*   **Objective**: Unify the server shutdown teardown sequence inside the application host lifecycle.
*   **Files changed**: `backend/core/application.py` (`ApplicationHost.stop()` is now async and executes registered cleanup hooks LIFO with error isolation; `register_cleanup_hook()` added; `dispose()` clears hooks), `backend/core/bootstrap.py` (registers ApplicationHost into the container), `backend/core/runtime_facade.py` + `backend/core/services.py` (`application_host` accessor), `backend/server.py` (`_unified_shutdown()` single cleanup orchestrator registered as hook; `shutdown_event`, frontend `shutdown`, and `stop_audio` all delegate to `_app_host.stop()`), `backend/tests/test_phase_4_5.py` (new regression suite).
*   **Delivered**: One shutdown path for all exit scenarios: summary save → AudioLoop stop → loop-task cancel (awaited, 1s cap) → authenticator stop → session detach → EventBus `session.shutdown` publish. `stop()` idempotent; hook errors non-fatal; hooks LIFO.
*   **Verification**: `tests/test_phase_4_5.py` — 8/8 pass: LIFO order, idempotency, error isolation, stop-before-start no-op, dispose clears hooks, ApplicationHost DI registration, RuntimeFacade access, AST check that all three shutdown handlers delegate to `_app_host.stop()` with no inline cleanup.
*   **Note**: Test consolidation (moving `core/`/`brain/` phase tests into `backend/tests/`) deferred — blocked on pytest not being installed in the lumina env; tracked under deferred debt.
*   **Dependencies**: Milestone 4.4.

---

## Immediate Priorities
**Phase 4 (Stable Runtime Recovery) is complete.** The next phase of work is **Phase 5**, whose design direction (cognitive architecture: BrainCore, Planner, Skill Registry) has been drafted and awaits milestone breakdown. Immediate priorities:
1.  Provision pytest/pytest-asyncio in the lumina conda env and consolidate the `core/`/`brain/` phase tests into `backend/tests/` (deferred 4.5 item).
2.  Begin Phase 5 milestone 5.1 (BrainCore skeleton) upon approval.
3.  Keep the DI/lifecycle architecture frozen — new capabilities register through Bootstrapper and cleanup hooks, never through new globals.

---

## Documentation Changelog
*   **2026-07-17 — Phase 4 completed**:
    *   Marked Phase 4 as ✅ Completed (Milestones 4.1–4.5); Phase 3 as ✅ Completed.
    *   All Phase 4 technical-debt items marked resolved with milestone references; deferred items split into their own list.
    *   Added completed Milestone 4.4 (ServiceAccessor/DI finalization) and 4.5 (unified lifecycle) sections with delivered/verification details.
    *   Full completion report: `Docs/Phase_4_Completion_Report.md`.
*   **Earlier**:
    *   Marked Phase 2 and Phase 3 as `🟡 Partially Complete` to reflect real repository state.
    *   Marked Phase 4 as `❌ Not Started` and labeled it as the Current Phase.
    *   Added a verified `Current Technical Debt` section highlighting global state issues, multiple `MemoryStore` handles, and port recovery bugs.
    *   Added a detailed `Phase 4 Implementation Plan` covering Milestones 4.1 to 4.5.
