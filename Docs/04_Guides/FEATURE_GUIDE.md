# LUMINA — Feature & Phase Guide

A complete walkthrough of how LUMINA works today: every subsystem built, how the
phases fit together, and how data flows from a user request to a stored evolution
recommendation.

This document is descriptive (how it works). For the authoritative phase list and
governance, see `Docs/TRUTH/ENGINEERING_ROADMAP.md`; for architecture decisions
see `Docs/TRUTH/adr/`.

---

## 1. What LUMINA Is

LUMINA is a local-first, voice-capable desktop AI assistant: Electron + React
frontend, FastAPI + Socket.IO backend, Gemini Live audio, and a decoupled
"Brain" cognitive layer. The runtime core (DI container, event bus, execution
pipeline, runtime facade) is deliberately **frozen and stable**; capabilities
grow around it, never by rewriting it.

---

## 2. Foundations (Phases 0–4, archived)

The earliest phases built the stable runtime and are complete/frozen:

- **Phase 1 — Runtime Foundation**: thread-safe Dependency Injection container,
  transaction-managed `BrainState`, wildcard `InProcessEventBus`, sealed
  `RequestPipeline`, and the central `RuntimeFacade`.
- **Phase 2 — Brain Runtime & State Migrations**: state migrated into
  `BrainState`; socket/disconnect handlers moved onto the EventBus; tool calls
  wrapped in `ExecutionContext`.
- **Phase 3 — Architectural Migration**: `SessionManager`, `ServiceAccessor`;
  `server.py` decoupled from `AudioLoop` internals.
- **Phase 4 — Stable Runtime Recovery**: dynamic port scanning, graceful
  shutdown, `SettingsSchema` self-healing, legacy bypass removal.

Everything after this is the **Cognitive Architecture** (Phase 5) and the
**Evolution Engine** (Phase 6).

---

## 3. Cognitive Architecture — Phase 5

### 5.1 Brain Core
`BrainCore` is the single orchestration authority. Per request it: builds a
`BrainContext` (via `ContextBuilder`), plans (via a planner), executes tasks (via
`SkillManager`), aggregates a `BrainResult`, and attaches a `Reflection`. It holds
no business logic itself — every step is an injected collaborator. Value objects
(`BrainRequest`, `BrainContext`, `Plan`, `Task`, `BrainResult`, `Reflection`) are
frozen pydantic models.

### 5.2–5.3 Planning & Skills
- `RulePlanner` — deterministic pattern→Plan mapping (e.g. navigation intents).
- `LLMPlanner` — model-backed planner (inert until a model gateway is bound).
- `PlannerChain` — ordered fallback: RulePlanner → LLMPlanner.
- `SkillManager` / `SkillRegistry` — execute a `Task` into a `SkillResult`.

### 5.5 Capability Layer
Skill metadata + capability discovery so planning can pick skills by capability
rather than hardcoded ids (`CapabilityResolver`), with a safe fallback.

### 5.6 Workspace Memory
Per-project structured memory:
- `WorkspaceMemory` — in-memory records (project info, decisions, notes, tasks).
- `WorkspaceMemoryStore` — JSON persistence (atomic save, safe load).
- `WorkspaceMemoryManager` — owns the current memory (current/switch/save/clear).
- `WorkspaceSync` — follows `ProjectManager` to keep the active workspace in step.
- `ContextBuilder` reads the current workspace snapshot into
  `BrainContext.workspace_ctx` (read-only).

### 5.7 Reflection Engine
`ReflectionEngine` — pure, deterministic, read-only post-execution evaluator.
After execution, `BrainCore` calls it exactly once and attaches the `Reflection`
to `BrainResult`. It never fails a request (errors → `reflection=None`).

### 5.8 Workspace Activation
`RuntimeFacade.activate_workspace()` is the single runtime entry point that
follows a project switch into `WorkspaceMemory` (delegating to `WorkspaceSync`).
Idempotent, flag-gated (default off → byte-identical runtime), failure-safe.

### 5.9 Workspace Reasoning (read-only retrieval → planning → prompting)
A deterministic, read-only retrieval layer feeding planning and prompting:

- **WorkspaceRetriever** (5.9.2) — the only retrieval implementation.
  Case-insensitive substring + exact-tag matching over the active workspace
  snapshot. No LLM, embeddings, vectors, or graph.
- **Recall services** (5.9.3–5.9.6) — thin, retrieval-free wrappers:
  `DecisionRecall`, `NotesRecall`, `TaskRecall`, `ArchitectureRecall`. Each
  delegates to the retriever with a fixed record type; all reuse the generic
  `WorkspaceRetrievalResult`.
- **Workspace-aware Planning** (5.9.7) — `ContextBuilder` (the sole enrichment
  point) runs recall once per request and packs results into a frozen
  `WorkspaceRecallContext` on `BrainContext`. The planner reads it; it never
  retrieves.
- **Workspace-aware Prompting** (5.9.8) — `PromptWorkspaceContext`, a frozen
  prompt-safe projection (lists of plain strings only). It is the ONLY object
  allowed to cross into prompt generation (ADR-0007).
- **Project Context Injection** (5.9.9) — `prompt_builder.py` formats
  `PromptWorkspaceContext` into a deterministic prompt section; empty →
  byte-identical prompt.

Boundary (ADR-0007): retrieval happens exactly once, in ContextBuilder. Planners
and prompt builders never retrieve; the workspace layer never imports planning or
core.

---

## 4. Evolution Engine — Phase 6

The Evolution Engine is an **analysis layer** (ADR-0008). It observes, measures,
analyzes, evaluates, and recommends. It **never mutates runtime**, rewrites
planners, edits prompts, creates skills, or writes memory. Phase 6 decides WHAT
should evolve; Phase 7 (Skill Creator, complete) performs the approved evolution
behind human approval. Every component is **dormant** — registered in DI but
consumed by no runtime path, so runtime stays byte-identical.

Pipeline (each layer consumes only the previous layer's immutable output):

```
Execution → Reflection
      → EvolutionObserver → EvolutionObservation → EvolutionStore (append-only)
      → StrategyEvaluator  → StrategyAnalysis
      → PerformanceAnalyzer → PerformanceAnalysis ─┐
                                                    ├─► RecommendationEngine
      MemoryConsolidator → ConsolidationProposalSet ┘        ↓
                                              EvolutionRecommendationSet → [Phase 7]
```

- **6.1 Reflection Learning** — `EvolutionObserver` reads a `Reflection`
  (read-only) and appends an immutable `EvolutionObservation` to the append-only
  `EvolutionStore`.
- **6.2 Strategy Improvement** — `StrategyEvaluator` aggregates stored
  observations into a `StrategyAnalysis` (per-strategy success rate, latency).
  Reads the store only; never Reflection.
- **6.3 Performance Analysis** — `PerformanceAnalyzer` measures a
  `StrategyAnalysis` into a `PerformanceAnalysis` (reliability, failure ratio,
  consistency, stability, efficiency, best/worst strategy). Measurement only.
- **6.4 Memory Consolidation** — `MemoryConsolidator` scans a memory snapshot
  (read-only) and proposes duplicate consolidations as an immutable
  `ConsolidationProposalSet`. Never writes memory.
- **6.5 Self Evolution** — `RecommendationEngine` consumes `PerformanceAnalysis`
  + `ConsolidationProposalSet` and emits an immutable
  `EvolutionRecommendationSet` (e.g. `improve_strategy`, `keep_strategy`,
  `review_required`, `merge_memory`, `observe_more`). Descriptive only — decides
  WHAT should evolve, performs nothing.
- **6.6 Validation & Freeze** — full pipeline validated (deterministic, immutable,
  append-only, isolated, dormant); Phase 6 marked COMPLETE · VALIDATED · FROZEN.

All evolution models are frozen and serializable; all ids are deterministic (no
UUID, no timestamps, no randomness).

---

## 4b. Skill Creator — Phase 7

The Skill Creator is a deterministic **compiler pipeline** (ADR-0010) that turns
an approved evolution recommendation into an installed, registered skill. Ten
stages, each a small dormant DI-registered class producing exactly one frozen
immutable artifact; no stage mutates a prior artifact (ADR-0012). Implemented in
`backend/brain/skill_creator/`. Full detail in `Docs/TRUTH/pipeline/01–10` and
ADR-0009–0013.

```
EvolutionRecommendationSet
 → 01 Builder       → SkillBlueprintSet
 → 02 Verifier      → VerificationResult
 → 03 Generator     → GenerationResult
 → 04 Tester        → TestResult
 → 05 Approver      → ApprovalRecord      (mandatory human gate)
 → 06 Installer     → InstallationRecord  (first filesystem write)
 → 07 Registry      → RegistryEntry       (append-only)
 → 08 Lifecycle     → LifecycleEvent[]    (append-only)
 → 09 Marketplace   → MarketplaceManifest (descriptive; no networking)
 → 10 Rollback      → RollbackRecord      (reverses installation)
```

- **7.1 Foundation** — contracts (`ISkillCreator`, frozen `SkillBlueprint`).
- **7.2 Blueprint Builder** — deterministic recommendation→blueprint mapping;
  schema hardened + frozen in 7.2.5/7.2.6/7.2.7 (ADR-0011).
- **7.3 Verification** — static checks (schema/capabilities/permissions/risk).
- **7.4 Generation** — deterministic package descriptors; gated on verification.
- **7.5 Testing** — static category checks (unit/determinism/safety); gated on generation.
- **7.6 Approval** — mandatory human gate; never auto-approves.
- **7.7 Installation** — materializes files to disk; idempotent; gated on approval.
- **7.8 Registry** — append-only catalog keyed by semantic fingerprint.
- **7.9 Lifecycle** — append-only state events (activate/deactivate/archive/supersede).
- **7.10 Marketplace** — portable manifest; descriptive, no networking.
- **7.11 Rollback** — reverses only installer-created files; idempotent.

Every stage: deterministic, immutable output, gated on the prior artifact,
dormant in DI (no runtime consumer yet — that is Phase 8, the Skill Runtime).

---

## 5. Determinism & Boundaries (why it's safe)

- **Frozen core**: runtime core is never modified by later phases.
- **Single enrichment point**: only `ContextBuilder` enriches `BrainContext`.
- **Read-only analysis**: Workspace Reasoning and the Evolution Engine only read;
  they never mutate runtime, memory, prompts, or planners.
- **Determinism**: substring/tag retrieval, aggregation, measurement, and
  recommendation are pure functions of their inputs — same input, byte-identical
  output.
- **Dormancy**: Evolution components are registered but never auto-invoked;
  runtime behavior is byte-identical to Phase 5.
- **Human approval**: any runtime-visible evolution (Phase 7 Approval stage)
  stays behind a mandatory human approval gate.

---

## 6. Current Status

- Phase 5 (Cognitive Architecture / Workspace Reasoning): **COMPLETE · FROZEN**.
- Phase 6 (Evolution Engine): **COMPLETE · VALIDATED · FROZEN**.
- Phase 7 (Skill Creator): **COMPLETE · VALIDATED · FROZEN** — 10-stage pipeline
  consuming `EvolutionRecommendationSet`, dormant in DI.
- Phase 8 (Skill Runtime): **COMPLETE · VALIDATED · FROZEN** — consumes
  `RegistryEntry` to use created skills. **8.1–8.13 + Validation & Freeze**
  (…Persistence, Runtime Pipeline Orchestrator, Failure Recovery, Runtime
  Validation): `RegistryDiscovery` projects the
  frozen registry into read-only `DiscoveredSkill` records; `CapabilityMatcher`
  ranks them semantically (exact 100 / alias 80 / tag 60) depending only on
  `IRegistryDiscovery`; `RuntimePipeline` (8.11) coordinates all ten stages
  (discovery → … → persistence) as a pure fail-fast coordinator; `FailureRecovery`
  (8.12) turns a failed `RuntimePipelineResult` into a descriptive `RecoveryPlan`
  (decides WHAT to recover, performs nothing); `RuntimeValidator` (8.13) asserts
  the result's structural integrity into a `ValidationReport` (checks, repairs
  nothing). All via `RuntimeFacade` (`registry_discovery`, `capability_matcher`,
  …, `runtime_pipeline`, `failure_recovery`, `runtime_validator`), dormant in DI;
  runtime byte-identical.

Test coverage: full Phase 5 + 6 + 7 + 8 regression suite passing (**913 tests**;
214 Phase 7, 219 Phase 8).
