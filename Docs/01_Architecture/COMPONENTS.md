# Lumina V2 Core Component Sheets

This document catalogs the concrete class design, constraints, and files for every core V2 subsystem.

---

## 1. Dependency Injection Container (`backend/core/container.py`)

- **Class**: `DependencyContainer`
- **Responsibility**: Wires concrete object instances or factory methods to abstract interface contracts.
- **Constraints**:
  - Thread-safe register operations using thread locks.
  - Supports transient bindings (instantiated per query) and singleton bindings (cached after first resolve).
  - Explicit `override()` method allows active loop re-registration on client reconnects.

---

## 2. Dynamic Bootstrapper (`backend/core/bootstrap.py`)

- **Class**: `Bootstrapper`
- **Responsibility**: Loads the system configuration schema, resolves environment settings, and registers core services at startup.
- **Wired Services**:
  - `IBrainState` -> `BrainState`
  - `IEventBus` -> `InProcessEventBus`
  - `IPipeline` -> `RequestPipeline`
  - `IPlanner` -> `Planner`

---

## 3. Core Runtime Facade (`backend/core/runtime_facade.py`)

- **Class**: `RuntimeFacade`
- **Responsibility**: Exposes simple, strongly-typed adapters (`brain_state_adapter`, `event_bus_adapter`, `pipeline_adapter`) to decouple callers from raw container queries.
- **Method**: `.new_execution_context_adapter()` yields a new contextual boundary per user request.

---

## 4. BrainState State Sandbox (`backend/brain/state.py`)

- **Class**: `BrainState`
- **Responsibility**: Manages the runtime transaction-safe memory state of the AI assistant (active calls, timers, user turn counters).
- **Design Constraints**:
  - **Pydantic Validation**: Backed by a strongly-typed Pydantic model (`BrainStateModel`).
  - **Thread Safety**: Guarded by a re-entrant lock (`threading.RLock()`).
  - **Read Queries**: Copy and return a frozen `BrainSnapshot`.
  - **Atomic Transactions**: Mutations occur inside a `transaction()` context manager. Changes apply atomically on successful exit; failures roll back the state to the pre-transaction state.

---

## 5. EventBus Pub/Sub Gateway (`backend/brain/events.py`)

- **Class**: `InProcessEventBus`
- **Responsibility**: Handles local, in-memory event publishing and subscription dispatching.
- **Design Constraints**:
  - **Wildcard Segment Matching**: Splitting topics by dot separators. `*` matches a single segment; trailing `**` matches all downstream segments (e.g. `session.*`, `dashboard.**`).
  - **Error Isolation**: Catches exceptions in callback handlers so a failing handler does not disrupt delivery to other subscribers.
  - **Async & Sync Support**: Supports both asynchronous `publish()` / `subscribe()` and synchronous convenience methods `publish_sync()` / `subscribe_sync()`.

---

## 6. Request Pipeline Middleware Stack (`backend/core/pipeline.py`)

- **Class**: `RequestPipeline`
- **Responsibility**: Runs contextual requests (like `create_quest`) through a linear stack of interceptor middlewares.
- **Design**: Sealed at bootstrap time to prevent runtime changes. Supports cancellation tokens to abort request execution gracefully.

---

## 7. ExecutionContext Contextual Tracing (`backend/core/context.py`)

- **Class**: `ExecutionContext`
- **Responsibility**: Holds tracing metadata (`context_id`, `correlation_id`, `client_sid`, and `brain_snapshot`) for a single user turn or Socket event.
- **Methods**: `.child()` creates nested tracking hierarchies, passing down the parent's `correlation_id` automatically.
