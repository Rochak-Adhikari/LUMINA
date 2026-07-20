# LUMINA — Architecture (Workspace Reasoning)

Companion to `Docs/TRUTH/ENGINEERING_ROADMAP.md`. Documents the Phase 5.9 Workspace
Reasoning architecture. Decision reference:
`Docs/TRUTH/adr/ADR-0007-workspace-context-boundary.md`.

## Workspace Reasoning Dependency Graph

```
WorkspaceMemory        (structured per-project storage)
      ↓
WorkspaceRetriever     (deterministic, memory-only retrieval)
      ↓
Recall Services        (DecisionRecall / NotesRecall / TaskRecall / ArchitectureRecall)
      ↓
ContextBuilder         (SOLE enrichment point — retrieval happens here, once)
      ↓
WorkspaceRecallContext (frozen recall container on BrainContext)
      ↓
PromptWorkspaceContext (frozen, prompt-safe projection — List[str] only)
      ↓
Prompt Builder         (brain/planning/prompt_builder.py)
      ↓
Planner                (consumes prepared context)
      ↓
LLM
```

## Invariants

- **ContextBuilder is the ONLY enrichment point.** Retrieval and recall occur
  there, exactly once per request.
- **The planner never retrieves.** It reads the prepared `BrainContext`
  (`workspace_recall`, `prompt_workspace`) only.
- **The prompt builder never retrieves.** It consumes only
  `PromptWorkspaceContext`.
- **The workspace layer never crosses directly into planning.** `brain.workspace`
  imports neither `brain.planning` nor `brain.core`; the graph is acyclic.
- **Retrieval is deterministic** — case-insensitive substring + exact tag
  matching, insertion order preserved. No LLM/embeddings/vector/graph.
- **Context models are frozen and append-only** — new recall kinds add fields;
  existing fields are never renamed, reordered, or removed.

## Boundary

`PromptWorkspaceContext` is the only object allowed to cross into prompt
generation. Prompt builders MUST NEVER receive `WorkspaceMemory`,
`WorkspaceSnapshot`, `WorkspaceRetriever`, `RetrievalHit`,
`WorkspaceMemoryManager` / Store, Recall services, `WorkspaceRecallContext`,
`WorkspaceSync` / Activation, or any runtime/mutable object. See ADR-0007.

## Evolution Engine Dependency Graph (Phase 6 — COMPLETE · FROZEN)

The Evolution Engine is an analysis layer. It observes and recommends; it never
mutates runtime. Recommendations flow forward to Phase 7 (Skill Creator), which
performs the approved evolution behind human approval. Reference:
`Docs/TRUTH/adr/ADR-0008-evolution-engine.md`,
`Docs/TRUTH/PHASE_6_ROADMAP.md`.

```
Execution
   ↓
Reflection
   ↓
Evolution Engine        (observe / analyze / evaluate / recommend)
   ↓
Recommendations         (immutable)
   ↓
Phase 7 Skill Creator   (consumes approved recommendations)
   ↓
Approved Metadata
```

The Evolution Engine NEVER flows into runtime mutation. There is no
`Evolution Engine → runtime mutation` edge. The only path from recommendations
to runtime is through Phase 7, behind human approval.

## Skill Creator Pipeline (Phase 7 — COMPLETE · FROZEN)

A deterministic 10-stage compiler pipeline (ADR-0010) that turns an approved
evolution recommendation into an installed, registered skill. Each stage is a
small dormant DI-registered class producing exactly one frozen immutable
artifact; no stage mutates a prior artifact (ADR-0012, append-only provenance).
Implemented in `backend/brain/skill_creator/`. Per-stage detail:
`Docs/TRUTH/pipeline/01–10`; decisions: ADR-0009–0013.

```
EvolutionRecommendationSet
   → 01 Builder      → SkillBlueprintSet
   → 02 Verifier     → VerificationResult
   → 03 Generator    → GenerationResult
   → 04 Tester       → TestResult
   → 05 Approver     → ApprovalRecord      (mandatory human gate)
   → 06 Installer    → InstallationRecord  (first filesystem write)
   → 07 Registry     → RegistryEntry       (append-only)
   → 08 Lifecycle    → LifecycleEvent[]    (append-only)
   → 09 Marketplace  → MarketplaceManifest (descriptive; no networking)
   → 10 Rollback     → RollbackRecord      (reverses installation)
```

Invariants: deterministic (same input → byte-identical output; no
UUID/timestamp/random), each stage gated on the prior artifact, all stages
dormant in DI (no runtime consumer yet — that is Phase 8, the Skill Runtime).

## Status

- Phase 5.9 — Workspace Reasoning: **COMPLETE · VALIDATED · FROZEN**.
- Phase 6 — Evolution Engine: **COMPLETE · VALIDATED · FROZEN**.
- Phase 7 — Skill Creator: **COMPLETE · VALIDATED · FROZEN**.
- Phase 8 — Skill Runtime: **NOT STARTED**.
