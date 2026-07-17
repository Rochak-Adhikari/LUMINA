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
| **Phase 2** | Brain Architecture | 🟡 Partially Complete | The sandbox state class (`brain/state.py`) and pub/sub event bus (`brain/events.py`) are implemented and tested, but their full integration within the active server routes remains incomplete due to legacy global state dependencies, inline constructor instantiation of resource managers, and hardcoded socket ports. |
| **Phase 3** | Interface Refactor & Clean Architecture | 🟡 Partially Complete | The `SessionManager` (`core/session.py`) and `ServiceAccessor` (`core/service_accessor.py`) interfaces are implemented, but the active backend execution path (`server.py`, `lumina.py`) has not yet been fully refactored to route queries and loops exclusively through these abstractions, bypassing them in favor of legacy globals. |
| **Phase 4** | **Stable Runtime Recovery** | 🟡 In Progress | **Current Phase**. Milestone 4.1 (graceful port recovery) is complete: startup keeps port 8000 when free and scans 8001–8009 only when 8000 is occupied. Remaining milestones (4.2–4.5) still pending. |
| **Phase 5** | Memory Engine | ❌ Not Started | Planned future phase. Focuses on semantic memory storage, local vector search indexes, knowledge graph structures, and project/workspace context maps. |
| **Phase 6** | Planning Engine | ❌ Not Started | Planned future phase. Focuses on structured task decomposition, reasoning chains, dynamic tool binding, and adaptive execution planners. |

---

## Current Technical Debt

Every item below represents a verified dependency or architectural gap present in the current codebase:

*   **Multiple MemoryStore Instances**: `server.py` implements its own cached `_fallback_memory_store` pointing directly to `"lumina_memory.db"`, while `AudioLoop` (`lumina.py`) constructs its own separate connection at startup, resulting in redundant SQLite connection handles and bypassing the DI registration.
*   **AudioLoop Constructs Dependencies Inline**: `AudioLoop.__init__` instantiates `MemoryStore` and `ProjectManager` directly on disk rather than resolving them via the DI container or accepting them as constructor arguments.
*   **Remaining server.py Globals**: Core states (`audio_loop`, `loop_task`, `authenticator`, `kasa_agent`) are declared as globals in `server.py` and modified directly by event handlers instead of being managed inside `SessionManager`.
*   **Port Recovery** ✅ *Resolved (Milestone 4.1)*: The startup routine previously ran `uvicorn.run` hardcoded to port `8000` with no recovery. It now keeps 8000 when free and scans 8001–8009 only when 8000 is occupied, logging each decision.
*   **Legacy Shutdown Path**: `server.py` uses legacy shutdown paths in `shutdown_event()` that directly reference `audio_loop` globals instead of cleanly routing the teardown through the DI-resolved `SessionManager`.
*   **Tests Not Fully Consolidated**: Unit tests are scattered across core directories (`backend/core/`, `backend/brain/`) rather than being fully consolidated under `backend/tests/`.

---

## Phase 4 Implementation Plan

The objective of Phase 4 is to eliminate the technical debt identified above, stabilize startup/shutdown lifecycles, complete dependency injection, and achieve clean architecture alignment.

### Milestone 4.1: Graceful Startup, Port Recovery & Logging ✅ Complete
*   **Objective**: Implement a self-healing port recovery system to handle socket starvation, and improve system startup logs.
*   **Files changed**: `backend/server.py` (module-scope `is_port_free` / `select_startup_port` helpers + `__main__` entrypoint), `backend/tests/test_port_recovery.py` (new regression test).
*   **Delivered**: Port 8000 is preserved when free; only when occupied does startup scan 8001–8009 for the first free port. Descriptive `[STARTUP]` console output on free/occupied/recovered/failure. Range exhaustion raises an explicit `OSError` instead of an opaque uvicorn bind crash. The probe intentionally omits `SO_REUSEADDR` so it matches uvicorn's real bind on Windows.
*   **Verification**: 6/6 regression tests pass (stdlib `unittest`). Live probe confirmed: 8000 free → binds 8000; 8000 occupied → recovers to 8001.
*   **Note**: Frontend (`Ui_TEST/AppTest.jsx`) and Electron (`electron/main.js`) still hardcode `localhost:8000`; keeping 8000 canonical when free preserves that contract. Wiring clients to a recovered port is out of scope for 4.1.
*   **Dependencies**: Phase 1 container setup.

### Milestone 4.2: Dependency Injection for AudioLoop
*   **Objective**: Refactor `AudioLoop` initialization to receive its `MemoryStore` and `ProjectManager` dependencies dynamically via dependency injection, resolving inline constructor instantiation.
*   **Files expected to change**: `backend/lumina.py`, `backend/core/bootstrap.py`
*   **Expected deliverables**: Refactored `AudioLoop` constructor accepting dependency interfaces, updated container registry to manage their lifecycles.
*   **Verification criteria**: Successful DI container boot and instantiation of `AudioLoop` using injected dependencies.
*   **Dependencies**: Phase 1 DI container.

### Milestone 4.3: Decouple Global State & Wire SessionManager
*   **Objective**: Eradicate the scattered global variables (`audio_loop`, `loop_task`, `authenticator`, `kasa_agent`) inside `server.py` by fully routing loop lifecycle and state queries through `SessionManager`.
*   **Files expected to change**: `backend/server.py`, `backend/core/session.py`
*   **Expected deliverables**: No global handles representing active loops/connections inside handlers.
*   **Verification criteria**: Event handlers query active sessions and authenticators through `SessionManager`.
*   **Dependencies**: Milestone 4.2.

### Milestone 4.4: Authoritative ServiceAccessor Integration
*   **Objective**: Clean up legacy lookup functions (like `_get_memory_store()`) and route all CRUD endpoint queries exclusively through the DI-resolved `ServiceAccessor` (`_svc.memory_store`).
*   **Files expected to change**: `backend/server.py`, `backend/core/service_accessor.py`
*   **Expected deliverables**: Total elimination of legacy fallback lookup paths in server routes.
*   **Verification criteria**: CRUD tests confirm all queries resolve via DIAccessor context.
*   **Dependencies**: Milestone 4.3.

### Milestone 4.5: Clean Shutdown Teardown & Test Consolidation
*   **Objective**: Unify the server shutdown teardown sequence inside the application host lifecycle, and move remaining unit tests from `core/` and `brain/` directories into `backend/tests/`.
*   **Files expected to change**: `backend/server.py`, `backend/core/application.py`, test file locations.
*   **Expected deliverables**: Graceful teardown loop sequence on signal intercept/FastAPI shutdown, fully consolidated tests folder structure.
*   **Verification criteria**: Pytest runs clean from `backend/tests/`, and SIGINT triggers graceful, non-hanging shutdown.
*   **Dependencies**: Milestone 4.4.

---

## Immediate Priorities
When **Phase 4 (Stable Runtime Recovery)** is initiated from this clean slate, the immediate goals will be:
1.  Verify clean system startup and graceful shutdown under starved system port allocations (8000–8009 range).
2.  Eliminate remaining technical debt and ensure memory manager lookups route solely through the DI container accessor (`_svc.memory_store`).
3.  Verify the robustness of the request execution pipeline under concurrency stress tests.
4.  Integrate the reorganized test directory structure with localized testing environments.

---

## Documentation Changelog
*   **Updated CURRENT_STATUS.md**:
    *   Marked Phase 2 and Phase 3 as `🟡 Partially Complete` to reflect real repository state.
    *   Marked Phase 4 as `❌ Not Started` and labeled it as the Current Phase.
    *   Added a verified `Current Technical Debt` section highlighting global state issues, multiple `MemoryStore` handles, and port recovery bugs.
    *   Added a detailed `Phase 4 Implementation Plan` covering Milestones 4.1 to 4.5.
