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

| Stage / Phase | Focus | Status |
| :--- | :--- | :--- |
| **Phase 1** | Runtime Foundation (DI, State, Pipeline, Bootstrapper) | **Completed** |
| **Phase 2** | Brain Architecture (Memory Store, Session Manager, Port Allocation) | **Completed** |
| **Phase 3** | Interface Refactor & Clean Architecture (Decoupled accessors, Event routing) | **Completed** |
| **Phase 4** | **Stable Runtime Recovery** (Technical debt elimination, startup/shutdown lifecycles) | **Current Phase**<br>*Not yet restarted. Implementation will begin from a clean repository.* |
| **Phase 5** | Memory Engine (Semantic storage, vector databases, workspace context) | **Planned** |
| **Phase 6** | Planning Engine (Task decomposition, reasoning chains, adaptive tool routing) | **Planned** |

### Future Horizons
*   **Skill Evolution**: Sandboxed skill generation, validation, and dynamic compilation workflows.
*   **Reflection**: Automated failure reviews, success scoring, and runtime optimization recommendations.
*   **Multi-Agent System**: Shared planning, execution, and review processes via common memory buffers.
*   **Continuous Learning**: Ongoing workspace feedback processing and refinement.

---

## Immediate Priorities
When **Phase 4 (Stable Runtime Recovery)** is initiated from this clean slate, the immediate goals will be:
1.  Verify clean system startup and graceful shutdown under starved system port allocations (8000–8009 range).
2.  Eliminate remaining technical debt and ensure memory manager lookups route solely through the DI container accessor (`_svc.memory_store`).
3.  Verify the robustness of the request execution pipeline under concurrency stress tests.
4.  Integrate the reorganized test directory structure with localized testing environments.
