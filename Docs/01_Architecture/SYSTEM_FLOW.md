# Lumina V2 System Flows & Dependencies

This document specifies the interaction flows, execution sequences, and dependency regulations of Lumina V2.

---

## 1. Interaction Sequences

### Startup Sequence Flow

```mermaid
graph TD
    classDef step fill:#07090f,stroke:#3b82f6,stroke-width:1px,color:#3b82f6;

    A[1. Process Boot]:::step --> B[2. Parse settings.json & Run Pydantic validation]:::step
    B --> C[3. Apply environment Tool Clamp overrides]:::step
    C --> D[4. Bootstrapper registers Core Services in DI container]:::step
    D --> E[5. Start FastAPI + Socket.IO Server & Alarm Loop]:::step
    E --> F[6. Client connects & emits start_audio]:::step
    F --> G[7. Instantiate AudioLoop & attach to SessionManager]:::step
    G --> H[8. Register MemoryEngine overrides in DI container]:::step
    H --> I[9. Seed identity facts & run live Gemini session]:::step
```

### Shutdown Sequence Flow

```mermaid
graph TD
    classDef step fill:#07090f,stroke:#3b82f6,stroke-width:1px,color:#3b82f6;

    A[1. Shutdown Triggered]:::step --> B[2. Publish session.shutdown on EventBus]:::step
    B --> C[3. Save continuity Session Summary to SQLite]:::step
    C --> D[4. Stop AudioLoop: close mic, speaker, and queue loops]:::step
    D --> E[5. Detach active session & clear DI overrides]:::step
    E --> F[6. Save resolved settings.json & exit process]:::step
```

### User Request Turn Cycles

```mermaid
sequenceDiagram
    autonumber
    actor User as Client Frontend
    participant Server as server.py (Socket Gateway)
    participant Accessor as ServiceAccessor (_svc)
    participant Pipeline as RequestPipeline
    participant Gemini as Gemini Live Session

    alt Text Request Input
        User->>Server: emit("user_input", {"text": "..."})
        Server->>Accessor: Retrieve active project context & memories
        Server->>Pipeline: execute(PipelineContext)
        Pipeline-->>Server: Continue execution
        Server->>Gemini: Send assembled message payload (with memories)
    else Voice Request Input
        User->>Server: Stream raw mic audio chunks
        Server->>Gemini: Stream PCM bytes over live websocket connection
    end

    Gemini-->>User: Stream direct synthesized TTS audio output
    Gemini-->>Server: Callback transcription text
    Server->>Accessor: Update chat log & aggregate transcripts
```

### Tool Confirmation Gate Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Gemini as Gemini Live Session
    participant Loop as AudioLoop (lumina.py)
    participant Registry as ToolDispatcherRegistry
    participant Client as Frontend Client

    Gemini->>Loop: Returns Tool FunctionCall (e.g. click dangerous text)
    Loop->>Loop: Evaluate settings.json tool permissions
    alt Requires User Confirmation
        Loop->>Client: emit("tool_confirmation_request", {id, tool, args})
        Note over Client: Visual Popup Overlay shown to user
        Client-->>Loop: User clicks Approve (True) / Deny (False)
    else Relaxed Mode
        Note over Loop: Auto-confirms action
    end

    alt Confirmed
        Loop->>Registry: dispatch(FunctionCall)
        Registry-->>Loop: Return tool execution results
        Loop->>Gemini: Send FunctionResponse
    else Rejected
        Loop->>Gemini: Send cancellation/rejection response
    end
```

---

## 2. Dependency Graph & Import Regulations

To preserve modular boundaries and eliminate circular import risks, Lumina enforces a strict import hierarchy.

### Layer Hierarchy

```mermaid
graph TD
    classDef interface fill:#07090f,stroke:#3b82f6,stroke-width:2px,color:#3b82f6;
    classDef concrete fill:#07090f,stroke:#10b981,stroke-width:1px,color:#10b981;
    classDef entry fill:#07090f,stroke:#ef4444,stroke-width:2px,color:#ef4444;

    Server[server.py]:::entry
    Lumina[lumina.py]:::concrete
    RuntimeFacade[core/runtime_facade.py]:::concrete
    ServiceAccessor[core/service_accessor.py]:::concrete
    SessionManager[core/session.py]:::concrete
    DI[core/container.py]:::concrete
    BrainState[brain/state.py]:::concrete
    EventBus[brain/events.py]:::concrete
    Interfaces[core/interfaces.py]:::interface

    Server --> Lumina
    Server --> ServiceAccessor
    Server --> SessionManager
    Server --> DI
    
    Lumina --> RuntimeFacade
    Lumina --> DI
    
    RuntimeFacade --> Interfaces
    RuntimeFacade --> DI
    
    ServiceAccessor --> DI
    ServiceAccessor --> SessionManager
    
    SessionManager --> BrainState
    SessionManager --> EventBus
    
    BrainState --> Interfaces
    EventBus --> Interfaces
```

### Architectural Import Rules

1. **Decoupled Upward Notifications**: No module under `core/` or `brain/` is permitted to import `server.py` or `lumina.py`. All communication to higher layers must occur via EventBus topic publication.
2. **Virtual Registrations**: Since legacy data models (`MemoryStore`, `ProjectManager`) do not directly inherit from abstract classes, they are registered dynamically in `bootstrap.py` using standard ABC helper bindings (e.g. `IWorkspaceManager.register(ProjectManager)`).
3. **No Direct Thread Mutations**: Callers must never cache service objects returned by `ServiceAccessor` properties (like `_svc.memory_store`). They should query properties dynamically to avoid reference corruption across threads.
