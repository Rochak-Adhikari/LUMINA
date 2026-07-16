# Lumina - Official Long-Term Roadmap

This document outlines the strategic vision, architectural principles, and progression milestones for Lumina. It defines Lumina's transition from a stable foundation into a local-first, learning-enabled AI operating system.

---

## 1. Vision

Lumina is a local-first **AI Operating System** (AIOS) and conversational companion. 
*   **Not a Chatbot**: Lumina does not merely converse; she reasons, acts, and orchestrates.
*   **Not a Simple Assistant**: Lumina does not execute static commands; she plans, monitors, and learns dynamically.
*   **Extensible Reasoning**: The core engine remains stable, secure, and compact, while its capabilities grow dynamically through sandboxed, reusable **skills** generated on-the-fly.

---

## 2. Core Philosophy

*   **Stable Core**: The runtime core (DI container, state transactions, event bus, execution pipeline) is kept frozen and protected from runtime code injection.
*   **Extensible Skills**: Capabilities are modular. Adding new functionality means generating or registering a skill, never altering the core architecture.
*   **User Approval Loop**: All dynamically generated skills must be explicitly approved, compiled, and validated by the user before installation.
*   **Unified Cognition**: Long-term memory, planning, and execution reflection work in a cohesive feedback loop.
*   **Safety First**: Execution processes, local files, and network requests are bounded by strict policies.
*   **Local-First Priority**: Data, vector indexes, and processing occur locally on the user's desktop to preserve security and privacy.

---

## 3. Long-Term Layered Architecture

Lumina's system topology consists of decoupled layers, each serving a distinct operational boundary:

```
┌────────────────────────────────────────────────────────┐
│                      FRONTEND                          │
│          (Electron + React / Audio Stream)             │
└──────────────────────────┬─────────────────────────────┘
                           │ Socket.IO / REST
┌──────────────────────────▼─────────────────────────────┐
│                         API                            │
│           (FastAPI / Routing / Auth Gates)             │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│                        BRAIN                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │   Planner  │  Memory  │ Reflection │ Personality │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│                        TOOLS                           │
│   (Registered JSON Tool Specs & Execution Routers)     │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│                        SKILLS                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Browser  │  Files  │  Terminal  │  Custom Skills │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│                        MODELS                          │
│    (Local Gemini Live Audio / Local Embedding LLMs)    │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│                      WORKSPACE                         │
│           (Context Cache / SQLite / STL)               │
└────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

1.  **Frontend**: Manages the desktop interface, real-time audio capture/playback, facial tracking, and UI gesture widgets.
2.  **API**: Fast API and Socket.IO servers that handle authentication, command routing, and client-state synchronization.
3.  **Brain**: The reasoning center.
    *   *Planner*: Decomposes prompts into structured tasks and checks tool requirements.
    *   *Memory*: Retrives and injects identity, context-specific, and summary records.
    *   *Reflection*: Inspects execution logs, flags errors, and optimizes prompt models.
    *   *Personality*: Enforces companion guidelines, sentiment tracking, and voice tone rules.
4.  **Tools**: Declares standard interface definitions (schemas) and maps inputs to backend services.
5.  **Skills**: Encapsulated script packages that perform actual operations (like automating a browser, reading files, or connecting to developer APIs).
6.  **Models**: Handles model execution, speech-to-speech loops, and text embedding.
7.  **Workspace**: Persists memory records in SQLite, local settings, and project caches on disk.

---

## 4. Future Roadmap Milestones

### Phase 4: Stable Runtime Recovery (Current Phase)
*   **Goal**: Stabilize backend loop, complete dependency injection, cleanup startup/shutdown logic.
*   **Key Deliverables**:
    *   Eliminate technical debt in memory store retrieval.
    *   Enforce graceful shutdown handlers and starvation-free port scanning.
    *   Strengthen unit tests and regression testing scripts.

### Phase 5: Memory Engine
*   **Goal**: Build a multi-tier memory system.
*   **Key Deliverables**:
    *   Semantic Memory: Vector databases for fast contextual search.
    *   Knowledge Graph: Map concepts, entities, and project hierarchies.
    *   Workspace Memory: Tracking modifications and project-specific contextual logs.

### Phase 6: Planning Engine
*   **Goal**: Transition Lumina from single-turn responses to multi-step reasoning.
*   **Key Deliverables**:
    *   Task Decomposition: Break complex user requests into structured, executable chains.
    *   Tool Orchestration: Dynamically bind actions based on model plan suggestions.
    *   Adaptive Planning: Pause execution, prompt for inputs on failure, and recalculate paths.

### Phase 7: Skill Engine
*   **Goal**: Enable dynamic, user-approved capability generation.
*   **Key Deliverables**:
    *   Skill Registry: Safe loading and cataloging of reusable Python skill packages.
    *   Skill Sandbox: Run generated skills in sandboxed subprocess environments.
    *   Automatic Testing: Let the reflection engine test a generated skill before asking for installation permission.
    *   *System Integration*: **Lumina generates new skills as plugins, never by modifying the core engine files directly.**

### Phase 8: Reflection Engine
*   **Goal**: Create self-correcting execution pipelines.
*   **Key Deliverables**:
    *   Failure Analysis: Parse error logs and track exceptions to adjust prompt configurations.
    *   Success Scoring: Evaluate performance speed, accuracy, and latency metrics.
    *   Self-Optimization: Update contextual prompts automatically from past system correction events.

### Phase 9: Multi-Agent System
*   **Goal**: Orchestrate work via specialized, communicating roles.
*   **Key Agents**:
    *   *Planner Agent*: Handles decomposition and routing.
    *   *Execution Agent*: Drives terminal/tool runs.
    *   *Browser Agent*: Navigates web targets.
    *   *Coding Agent*: Reviews and writes scripts.
    *   *Reflection Agent*: Validates results.
    *   *Manager Agent*: Synchronizes state.
    *   *Coordination Rule*: **Specialized agents communicate and cooperate through shared planning registers and unified memory, never in isolated silos.**

### Phase 10: Autonomous Desktop Assistant
*   **Goal**: Enable secure, background workspace orchestration.
*   **Key Deliverables**:
    *   Scheduled Workflows: Execute tasks in the background on specific calendar schedules.
    *   Desktop Control: Safely manipulate window targets, files, and system processes.
    *   Continuous Learning: Dynamically adapt desktop behavior based on user habits and workspace trends.

---

## 5. Guiding Principles

1.  **Stable Core Over Features**: The core architecture must remain stable, frozen, and highly testable. Feature growth must occur within the skill layer.
2.  **Explicit Consent**: Every generated capability or script must be sandboxed, tested, versioned, and explicitly approved by the user before activation.
3.  **Core Foundations**: Memory, planning, and reflection are not accessories; they are core cognitive layers that drive all skills.
4.  **Resilience First**: Maintainability, safety, and transparency take precedence over rapid, unchecked capability growth.
