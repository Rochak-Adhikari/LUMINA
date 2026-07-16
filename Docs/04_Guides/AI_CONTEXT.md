# Lumina V2 - AI Coding Assistant Context

This document is the authoritative instruction card for all AI coding assistants (LLMs) modifying this repository. It must be read before performing any code generation, refactoring, or documentation edits.

---

## 1. Project Overview & Boundaries

Lumina is a private conversational AI companion designed for voice-first interactions. It is built to operate under strict architectural boundaries to preserve system security, performance stability, and companion role focus.

- **Nickname**: Luna
- **Role**: Support companion, design collaborator (CAD), and voice listener.
- **Language Style**: Casual Nepali/English code-swapped colloquial dialect ("timi" informal you).
- **Core backend**: Python, FastAPI, Socket.IO, Gemini Live API, and SQLite database.
- **Frontend**: React (Vite) and Electron desktop app container.

---

## 2. Current Architecture & Status

Lumina is currently in **Version 2.2.0**. The core architectural components are completely **frozen** and stable.

The infrastructure consists of:
1. **Dependency Injection Container** (`backend/core/container.py`): Lazy singleton registrations of core service contracts.
2. **BrainState Sandbox** (`backend/brain/state.py`): Pydantic-validated, transaction-managed state engine guarded by a re-entrant lock. Read snapshots are frozen; updates must be written via transaction context managers.
3. **In-Process EventBus** (`backend/brain/events.py`): Wilcard-segmented event publisher (e.g. `session.shutdown`, `dashboard.command`).
4. **SessionManager** (`backend/core/session.py`): Active loops binder and lifecycle synchronizer.
5. **ServiceAccessor** (`backend/core/service_accessor.py`): DI-first lookup bridge.

---

## 3. Strict Rules for AI Coding Assistants

### 🚫 Things AI Assistants Must NEVER Do

1. **Never implement future roadmap items**: Do not write code for Phase 5 (FAISS/FTS5 memories) or Phase 6 (autonomous plan graphs) unless explicitly requested.
2. **Never create placeholder code**: Writing `pass`, `NotImplementedError`, or Mock classes inside production modules is strictly prohibited. Everything implemented must be production-ready.
3. **Never redesign working architecture**: Do not rewrite the DI container, do not bypass the ServiceAccessor, do not replace the Pydantic state model, and do not introduce new frameworks.
4. **Never claim tests pass without running them**: You must actively run the test scripts via the terminal and verify the output before claiming a task is done.
5. **Never document non-existent features**: Every API, event, or guide you write must represent actual concrete implementations in the current repository.
6. **Never modify application code for layout tasks**: When performing documentation reorganizations or file cleanups, you must not edit any Python or configuration files.

### Always Do These

1. **Always inspect the repository before making changes**: Perform directory scans, search references, and read existing modules to understand conventions.
2. **Always resolve components via the DI container**: Use the `RuntimeFacade` or `ServiceAccessor` (`_svc.memory_store`, `_svc.project_manager`) to resolve services. Never instantiate `MemoryStore` or `ProjectManager` concrete classes directly.
3. **Always preserve historical comments and docstrings**: Keep existing code headers and architecture descriptions intact unless they are directly obsolete.
4. **Always follow the Conda environment rules**: Always use the active conda environment Python: `E:\AI\conda_envs\lumina\python.exe` to run check scripts and unit tests.

---

## 4. Coding Conventions

### DI Service Resolution
To resolve a manager, query it via `_svc` or `_facade` properties:
```python
# GOOD: resolves from container with proper handles
store = _svc.memory_store
if store:
    store.add_memory("fact", "...")

# BAD: instantiates duplicate SQLite handles
from memory_store import MemoryStore
store = MemoryStore("lumina_memory.db")
```

### BrainState Transactions
All updates to `BrainState` must occur within transaction boundaries:
```python
# GOOD: atomic update with automatic commit/rollback
with brain_state.transaction() as state:
    state.pending_confirmation_id = "123"

# BAD: modifying values directly on snapshot or state
brain_state.pending_confirmation_id = "123"
```

### Event Bus Publication
Any cross-cutting concerns (e.g. client disconnect, alarm triggers, dashboard pairing) must notify subscribers via the EventBus:
```python
# GOOD: decoupled pub/sub
await facade.event_bus_adapter.publish("session.disconnected", {"sid": sid})
```
