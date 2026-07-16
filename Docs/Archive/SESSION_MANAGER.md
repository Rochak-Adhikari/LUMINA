# Lumina V2 Session Manager Specification

This document details the design, properties, and lifecycle behaviors of `SessionManager` in Lumina V2.

---

## 1. Class Design & Purpose

`SessionManager` ([session.py](file:///e:/Lunina-with%20features%20added/backend/core/session.py)) centralizes ownership of the active `AudioLoop` session. In prior versions, this was managed via a mutable global variable (`audio_loop = None`) in `server.py`. 

### Responsibilities
* **Lifecycle Ownership**: Exposes properties to register (`attach()`) and release (`detach()`) the active session.
* **BrainState Synchronizer**: Updates the session connection status (`connected_at`) atomically in `BrainState` on registration changes.
* **Event Publisher**: Dispatches event notifications on lifecycle changes to the `EventBus`.
* **Access Delegation**: Exposes properties for sub-services (`memory_store`, `project_manager`, `session`) to decouple handlers from direct `AudioLoop` referencing.

---

## 2. API Contract

```python
class SessionManager:
    def __init__(self, brain_state: IBrainState, event_bus: IEventBus) -> None:
        """Initializes the manager. Starts with no active session."""

    def attach(self, audio_loop: Any) -> None:
        """
        Binds an active AudioLoop session.
        - Stores the session reference.
        - Writes `connected_at` timestamp inside BrainState.
        - Publishes 'session.audio_attached' event on the EventBus.
        """

    def detach(self) -> None:
        """
        Unbinds the active session.
        - Resets session pointers.
        - Triggers BrainState.reset_session().
        - Publishes 'session.audio_detached' event on the EventBus.
        """

    @property
    def audio_loop(self) -> Any:
        """Returns the active AudioLoop session or None."""

    @property
    def is_active(self) -> bool:
        """Returns True if a session is currently attached."""

    @property
    def memory_store(self) -> Any:
        """Returns the active session's memory store or None."""

    @property
    def project_manager(self) -> Any:
        """Returns the active session's project manager or None."""
```

---

## 3. Session Integration Walkthrough

The following state machine details session transitions:

```mermaid
stateDiagram-v2
    [*] --> Inactive : Initialization
    
    state Inactive {
        note right of Inactive : is_active = False<br/>audio_loop = None<br/>BrainState: connected_at = None
    }
    
    Inactive --> Active : attach(audio_loop)
    
    state Active {
        note right of Active : is_active = True<br/>audio_loop = Ref<br/>BrainState: connected_at = ts
    }
    
    Active --> Inactive : detach()
    Active --> Inactive : shutdown()
```

---

## 4. Operational Safety Guidelines

> [!IMPORTANT]
> **THREAD MUTATION SAFETY**: Mutating attach/detach actions are guarded by a Python threading `Lock` instance to prevent race conditions during rapid startup/shutdown triggers.
> **DELEGATION PATTERNS**: Callers must never cache service references returned by properties (like `session_manager.memory_store`). They should always request properties dynamically to ensure thread-safety and prevent stale references.
