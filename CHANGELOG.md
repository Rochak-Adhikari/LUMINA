# Changelog

All notable changes to LUMINA are documented here.

## Phase 5.9 — Workspace Reasoning

**Status: COMPLETE · VALIDATED · FROZEN**

Read-only, deterministic workspace reasoning layer feeding planning and
prompting. No runtime behavior changes — all new components are dormant
(not registered in DI) and default-empty.

### Completed Components

- **Workspace Memory** (5.6) — structured per-project records.
- **WorkspaceRetriever** (5.9.2) — deterministic, memory-only retrieval
  (case-insensitive substring + exact tag matching; insertion order preserved).
  No LLM/embeddings/vector/graph.
- **Recall services** — DecisionRecall (5.9.3), NotesRecall / TaskRecall /
  ArchitectureRecall (5.9.4–5.9.6). Thin, retrieval-free wrappers over the
  retriever; each reuses the generic `WorkspaceRetrievalResult`.
- **WorkspaceRecallContext** (5.9.7) — frozen, append-only recall container on
  `BrainContext`; every field always a valid result (no None state).
- **PromptWorkspaceContext** (5.9.8) — frozen, prompt-safe projection
  (`List[str]` fields only); the sole object allowed to cross into prompt
  generation.
- **Prompt Builder** (5.9.9 / renamed 5.9.10) —
  `brain/planning/prompt_builder.py`; deterministic workspace prompt section,
  empty-safe (byte-identical when empty).
- **Workspace-aware Planning** (5.9.7) — planner reads prepared context; never
  retrieves.
- **Workspace-aware Prompting** (5.9.8–5.9.9) — recalled knowledge injected into
  the LLM prompt via the frozen contract.

### Architecture Improvements

- Single enrichment point: ContextBuilder invokes recall exactly once per
  request.
- Strict acyclic dependency graph; the workspace layer never imports planning or
  core.
- Frozen, append-only context models.
- Prompt formatting isolated into a dedicated module (`prompt_builder.py`).

### ADR Added

- **ADR-0007 — Workspace Context Boundary**: `PromptWorkspaceContext` is the only
  object allowed to cross into prompt generation; documents the dependency graph
  and design principles.

### Testing Summary

- Dedicated suites per milestone (`tests/test_phase_5_9_step*.py`).
- Coverage: retrieval, recall delegation, context enrichment, prompt projection,
  prompt injection, determinism, frozen models, import whitelists, cycle checks.

### Regression Summary

- Full Phase 5 regression: **404 passed**, 0 failed.

### Boot Verification

- Clean boot; 0 tracebacks; 0 duplicate registrations.
- All workspace reasoning components verified DORMANT (unregistered in DI).

### Runtime Behavior

- **No runtime behavior changes.** Byte-identical: default-empty context yields
  no prompt injection; no DI / Bootstrap / RuntimeFacade / server changes.
