# Lumina V2 High-Level Architecture Specification

This document defines the core architecture, layers, and operational cycles of Lumina V2. It is the authoritative reference for the frozen V2 core platform.

---

## 1. High-Level Architecture

Lumina is a local-first conversational AI companion, structured as a modular backend communicating with a desktop client application. The backend separates reasoning (handled by the Gemini Live API session) from direct tool execution and context management.

### Layer Diagram

```
                ┌─────────────────────────────────────────┐
                │          User Interaction Layer         │
                │        (FastAPI / Socket.IO Gateway)    │
                └────────────────────┬────────────────────┘
                                     │
                        Session Management Layer
                        (SessionManager & ServiceAccessor)
                                     │
                                     ▼
                ┌─────────────────────────────────────────┐
                │               Brain Layer               │
                │   (AudioLoop / Gemini Live API Session) │
                └────────────────────┬────────────────────┘
                       ┌─────────────┴─────────────┐
                       ▼                           ▼
              ┌─────────────────┐         ┌─────────────────┐
              │   Skill Layer   │         │ Workspace Layer │
              │ (Tool Dispatch) │         │ (Project/Memory)│
              └────────┬────────┘         └─────────────────┘
                       │
             Headless Browser • CAD OpenSCAD • Kasa Smart Home • Moonraker 3D Printer
```

---

## 2. Core Architectural Components

### A. Dependency Injection Container (`backend/core/container.py`)
- **Type**: Thread-safe dynamic service registry.
- **Scope**: Registers all core services as lazy singletons, instances, or transient types at startup.
- **Service Override**: Enables dynamic override bindings for runtime instances (e.g. `IMemoryManager` and `IWorkspaceManager` overrides are registered when the active session initializes).

### B. Bootstrapper (`backend/core/bootstrap.py`)
- **Type**: Application configuration loader and container register.
- **Function**: Executes container registrations for core interfaces:
  - `IBrainState` (BrainState transaction state machine)
  - `IEventBus` (InProcessEventBus async pub/sub)
  - `IPipeline` (RequestPipeline interceptor chain)
  - `IPlanner` (Placeholder Planner coordinator)
  - `IMemoryManager` (Lazy resolved SQLite database)
  - `IWorkspaceManager` (Lazy resolved ProjectManager workspace)

### C. RuntimeFacade (`backend/core/runtime_facade.py`)
- **Type**: Strongly-typed access layer.
- **Function**: Acts as a safe facade wrapper over the raw DI container, exposing properties (`brain_state_adapter`, `event_bus_adapter`, `pipeline`) to separate contract querying from raw container resolution.

### D. SessionManager (`backend/core/session.py`)
- **Type**: Active loop controller and state tracker.
- **Function**: Unifies ownership of the active `AudioLoop` session, replacing module-level globals in `server.py`. Updates the session connection timestamps in `BrainState` and publishes lifecycle state changes (`session.audio_attached` / `session.audio_detached`) on the EventBus.

### E. ServiceAccessor (`backend/core/service_accessor.py`)
- **Type**: Dependency-inversion access bridge.
- **Function**: Resolves requests for `IMemoryManager` (SQLite store) and `IWorkspaceManager` (ProjectManager) by checking container registrations first, falling back to the active `AudioLoop` properties if the container is not yet fully initialized.

### F. EventBus Subsystem (`backend/brain/events.py`)
- **Type**: Zero-dependency asynchronous in-process Publish/Subscribe system.
- **Function**: Distributes decoupling notifications (e.g. `session.shutdown`, `dashboard.command`) to background workers. Supports wildcard topic matching (e.g. `session.*`, `**`) and handles errors in isolation to protect delivery loops.

### G. Memory Subsystem
- **SQLite Database (`backend/lumina_memory.db`)**: Holds raw factual and preference records.
- **MemoryStore (`backend/memory_store.py`)**: Abstracted SQLite interface providing CRUD capabilities.
- **MemoryEngine (`backend/memory_engine.py`)**: Handles FTS5 full-text indexing, FAISS semantic vector search (future capability), and access priority decay.
- **Service Access**: Resolves via `_svc.memory_store` to guarantee unified SQLite handle reuse.

### H. Tool Execution & Dispatch (`backend/core/tool_handlers.py`)
- **Type**: Centralized dispatcher registry.
- **Registry**: `ToolDispatcherRegistry` maps tool names to corresponding handlers.
- **Dispatch Flow**: `AudioLoop` intercepts Gemini Live `FunctionCall` packets, validates env clamp and settings permissions, prompts the user for gated operations (like browser typing/submitting), and executes via registered handlers.

---

## 3. Core System Lifecycles

### Startup Sequence

```
1. server.py executes (Process boot)
   ├── sys.stdout reconfigure -> UTF-8
   ├── Conda env verify (Require E:\AI\conda_envs\lumina)
   ├── load_settings() -> SettingsSchema validation & self-healing
   ├── _reapply_tool_clamp() -> enforce force-clamp environment rules
   └── Bootstrapper constructs -> Wires core container services

2. FastAPI startup_event()
   ├── KasaAgent init (if enabled)
   └── _reminder_alarm_loop() starts background execution task

3. Socket.IO start_audio Event (Client Connected)
   ├── Instantiate AudioLoop (lumina.py)
   ├── SessionManager.attach(audio_loop)
   ├── MemoryEngine init -> register IKnowledgeManager in container
   ├── _seed_owner_identity() seeds identity facts
   └── AudioLoop.run() task scheduled on event loop
```

### Shutdown Sequence

```
FastAPI shutdown_event()
   ├── Publish 'session.shutdown' on InProcessEventBus
   ├── Save session summary (continuity summary saved to SQLite)
   ├── audio_loop.stop() -> close pyAudio, flush buffers, stop tasks
   └── SessionManager.detach() -> clear container overrides
```
