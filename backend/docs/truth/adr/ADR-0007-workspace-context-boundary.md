# ADR-0007 — Workspace Context Boundary

**Status:** Accepted (Phase 5.9 freeze)
**Supersedes:** —
**Related:** docs/truth/ROADMAP.md (Phase 5.9 — Workspace Reasoning)

## Purpose

Establish a permanent architectural boundary between the workspace reasoning
layer (memory, retrieval, recall) and prompt generation. Prompt builders must
never gain access to retrieval or runtime objects. Exactly one immutable,
prompt-safe object — `PromptWorkspaceContext` — is allowed to cross into prompt
generation.

## Architecture

Workspace knowledge flows strictly downward through a single enrichment point:

- `WorkspaceMemory` holds structured records (storage only).
- `WorkspaceRetriever` performs the only retrieval (memory-only, deterministic).
- Recall services (`DecisionRecall`, `NotesRecall`, `TaskRecall`,
  `ArchitectureRecall`) are thin delegators over the retriever — no retrieval
  logic of their own.
- `ContextBuilder` is the SOLE enrichment point. It invokes recall once per
  request and builds `WorkspaceRecallContext`.
- `WorkspaceRecallContext` (frozen) carries the recall results on `BrainContext`.
- `PromptWorkspaceContext` (frozen) is a prompt-safe projection: only
  `List[str]` fields. Built solely via `from_recall`.
- The prompt builder (`brain/planning/prompt_builder.py`) formats
  `PromptWorkspaceContext` into a deterministic prompt section.
- The planner consumes the prepared context; it never retrieves.

## Dependency Graph

```
WorkspaceMemory
      ↓
WorkspaceRetriever
      ↓
Recall Services
      ↓
ContextBuilder
      ↓
WorkspaceRecallContext
      ↓
PromptWorkspaceContext
      ↓
Prompt Builder
      ↓
Planner
```

No reverse edges. The workspace layer never imports `brain.planning` or
`brain.core`. `brain.core.models` imports `brain.workspace.models` for the
context types only; the graph remains acyclic.

## Boundary Contract

Prompt generation may consume ONLY `PromptWorkspaceContext`. It MUST NEVER
receive any of:

- `WorkspaceMemory`
- `WorkspaceSnapshot`
- `WorkspaceRetriever`
- `RetrievalHit`
- `WorkspaceMemoryManager` / `WorkspaceMemoryStore`
- Recall services
- `WorkspaceRecallContext`
- `WorkspaceSync` / Workspace Activation
- any runtime or mutable object

## Design Principles

- Retrieval occurs exactly once, in ContextBuilder, per request.
- ContextBuilder is the sole enrichment point.
- The planner never retrieves.
- Prompt builders never retrieve.
- Retrieval is deterministic (case-insensitive substring + exact tag, insertion
  order preserved).
- Context models are frozen and append-only (new recall kinds add fields; existing
  fields are never renamed, reordered, or removed).
- The dependency graph is acyclic.
- The workspace layer never imports planning or core.

## Consequences

- Retrieval mechanics can evolve (semantic/graph/hybrid) behind the frozen
  interfaces without touching planners or prompt builders.
- Prompt generation is insulated from all retrieval and runtime detail.
- The boundary is enforced by tests (import whitelists, cycle checks) and by
  this ADR as the permanent reference.
