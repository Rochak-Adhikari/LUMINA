# Lumina V2 Core Architecture Specification

> **Version**: 2.2.0  
> **Status**: ARCHITECTURALLY FROZEN  
> **Last Updated**: July 2026  
> **Target Branch**: `refactor/interfaces-and-di`

---

## 1. System Identity & Boundaries

Lumina is a private conversational AI companion designed for voice-first interactions. It is built to operate under strict architectural boundaries to preserve system security, performance stability, and role focus.

| Property | Value |
|---|---|
| **Name** | Lumina |
| **Nickname** | Luna |
| **Creator** | Scepter (Rochak Adhikari) |
| **Role** | Conversational AI Companion |
| **Primary Language** | Modern colloquial Nepali (`ne-NP`) with natural English code-switching |

### Architectural Guardrails
* **No Direct OS Manipulation**: Core conversation engines are decoupled from hardware/OS. All device commands route deterministic requests through structured interfaces.
* **Passive Memory Storage**: Memory engines store contextual facts, user preferences, and summaries, but do not autonomously initiate actions or alter software pathways.
* **Single Active Turn**: A strict state-lock prevents parallel turn generation, suppressing duplicate voice streams and eliminating race conditions.

---

## 2. Structural Layer Overview

Lumina V2 introduces a decoupled, interface-first layer model to separate connection management from state persistence and request pipeline processing.

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           1. Application Entry                            │
│           (FastAPI / Socket.IO Server Gateway in server.py)               │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                           2. Service Resolution                           │
│        (Dependency Injection Container & RuntimeFacade Services)           │
└──────────┬──────────────────────────┬──────────────────────────┬──────────┘
           │                          │                          │
           ▼                          ▼                          ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│    3. BrainState    │    │     4. EventBus     │    │ 5. Request Pipeline │
│ (Pydantic Sandbox / │    │ (InProcessEventBus  │    │  (Structured execution│
│ atomic transactions)│    │ async pub/sub layer)│    │  middleware list)   │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

---

## 3. Subsystem Specifications

### A. Dependency Injection Container ([container.py](file:///e:/Lunina-with%20features%20added/backend/core/container.py))
* **Type**: Thread-safe dynamic service registry.
* **Binding Life Cycles**: Supports `instance`, `singleton` (lazy-initialized), `transient` (new allocation per query), and dynamic `override` (safe session recreation).
* **Usage**: Core services resolve their contracts (`IMemoryManager`, `IWorkspaceManager`, etc.) from the container, separating class definitions from runtime instance bindings.

### B. BrainState Sandbox ([state.py](file:///e:/Lunina-with%20features%20added/backend/brain/state.py))
* **Type**: Pydantic-validated transaction-managed state tree.
* **Design Pattern**:
  * **Immutable Snapshots**: Read queries copy a frozen `BrainSnapshot` representing a consistent point-in-time state.
  * **Atomic Transactions**: Mutations require a `transaction()` context manager. Changes apply atomically on exit; exceptions trigger automatic rollbacks.
  * **Thread Safety**: Guarded by an internal Re-entrant Lock (`RLock`).

### C. EventBus Subsystem ([events.py](file:///e:/Lunina-with%20features%20added/backend/brain/events.py))
* **Type**: Asynchronous in-process Publish/Subscribe system.
* **Features**: Supports concurrent topic matching, asynchronous deliveries, and synchronous notifications for critical startup hook sequences.
* **Core Topics**:
  * `session.audio_attached`: Triggered when an active `AudioLoop` is bound.
  * `session.audio_detached`: Triggered when session finishes or terminates.
  * `session.shutdown`: Published during FastAPI process shutdown.

### D. Request Execution Pipeline ([pipeline.py](file:///e:/Lunina-with%20features%20added/backend/core/pipeline.py))
* **Type**: Linear interceptor middleware stack.
* **Lifecycle**: Maps incoming actions through a sealed list of execution filters, providing cross-cutting validation, logging, and performance auditing without direct handler alterations.

---

## 4. Phase 3 Session & Service Bridge Layers

To bridge the gap between concrete runtime engines and V2 DI architectures, Phase 3 introduces two critical synchronization interfaces:

### SessionManager ([session.py](file:///e:/Lunina-with%20features%20added/backend/core/session.py))
* Centralizes control of active `AudioLoop` sessions, replacing module-level globals in `server.py`.
* Synchronizes session connect/disconnect timestamps with `BrainState` attributes.
* Publishes lifecycle changes on the `EventBus` to notify downstream subscribers.

### ServiceAccessor ([service_accessor.py](file:///e:/Lunina-with%20features%20added/backend/core/service_accessor.py))
* Safe bridge routing subsystem requests (`MemoryStore`, `ProjectManager`) first to the DI container.
* Falls back to properties of the active `AudioLoop` if early initialization is in progress or container registrations are incomplete.

---

## 5. Architectural Quality Attributes

> [!IMPORTANT]
> **AESTHETICS & VISUALS**: All UI adjustments must maintain clean, modern dark mode coordinates.
> **STABILITY & LATENCY**: The audio stream operates under a hard 20ms frame budget. Service access layers must not block the main asyncio loop.

---

*This document is locked and frozen. Modification to the core layers specified above requires a formal technical proposal and approval.*
