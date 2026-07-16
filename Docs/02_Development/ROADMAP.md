# Lumina V2 Development Roadmap

This document outlines planned future work for Lumina V2. Completed phases (Phases 1–4) are frozen and referenced here only as foundations.

---

## 1. Phase 5 — Memory Engine Upgrade

### Goal
Provide long-term, semantic memory retrieval that persists across user sessions and automatically prioritizes relevant facts.

### Motivation
The current memory database is a simple SQLite table with exact keyword matching. As the number of memories grows, simple keyword matches degrade in relevance. Semantic search and decay metrics are required to keep retrieved context concise.

### Tasks
- [ ] **FTS5 Integration**: Add full-text search indexing on `memories` content column in SQLite.
- [ ] **Vector Embeddings**: Implement a local embedding service (e.g. using a tiny SentenceTransformer model or calling a lightweight local API) and store embeddings in SQLite or a small FAISS index.
- [ ] **Relevance Scorer**: Combine FTS5 score + cosine vector similarity + recency weight + access frequency into a unified priority rank.
- [ ] **Decay Job**: Run background memory pruning or demotion (moving unused facts to a dormant state after prolonged inactivity).

### Acceptance Criteria
- Queries with zero exact keyword overlap but high semantic similarity (e.g., query "my job is coding" vs memory "preferred occupation is programmer") retrieve the correct fact.
- Semantic retrieval must execute in under 50ms to fit the audio turn budget.
- Unused memory items must decay in priority rank and demote to "dormant" state automatically.

### Dependencies
- Stable DI registration for `IKnowledgeManager` (completed in Milestone 4.6).
- `MemoryStore` SQLite handle.

### Status
- **Planned**

---

## 2. Phase 6 — Planning Engine Implementation

### Goal
Transform Lumina from a prompt-response chatbot into an autonomous planning coordinator capable of decomposing complex goals into multi-step tool execution plans.

### Motivation
Currently, when Gemini returns a function call, Lumina executes it immediately. If a user request requires multiple steps (e.g., "build a web scraper, extract the list, compile it to CSV, and commit it to git"), the model must reason step-by-step through successive live audio turns. A dedicated planner coordinates this locally and executes composite workflows.

### Tasks
- [ ] **IPlanner Contract**: Define the planner registration interface in `core/interfaces.py`.
- [ ] **Plan Coordinator**: Implement `PlannerCoordinator` that parses user goal, builds a plan graph (steps, tools, dependencies), and manages task execution loops.
- [ ] **EventBus Integration**: Publish plan lifecycle notifications (`plan.started`, `plan.step_success`, `plan.failed`) to allow live UI updates.
- [ ] **BrainState Integration**: Maintain active planning models and task steps inside `BrainState.planner_context`.

### Acceptance Criteria
- User goals requiring more than 3 steps execute to completion without intermediate user audio turns.
- Plan graph recovers from tool failures dynamically by scheduling retries or selecting alternative skills.
- The active plan and step progress displays in the client UI using standard socket events.

### Dependencies
- Frozen core DI container and InProcessEventBus (completed in Phase 1-3).
- `ToolDispatcherRegistry` central execution loop (completed in Milestone 4.2).

### Status
- **Planned**
