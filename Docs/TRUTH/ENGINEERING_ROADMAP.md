# LUMINA — ENGINEERING ROADMAP

**SINGLE SOURCE OF TRUTH (Engineering)**

This document is the permanent, frozen engineering implementation roadmap for LUMINA development. From this point onward, every development session, architecture discussion, and implementation milestone must conform to this document. If any future discussion conflicts with this roadmap, this roadmap always wins.

This is the engineering implementation roadmap. For long-term product vision, see `Docs/TRUTH/ROADMAP.md`.

---

## Project History

LUMINA development has progressed through multiple architecture phases, beginning from the earliest core architecture (Phase 0 / Phase 1 foundations) up through the Brain architecture.

Those historical implementation phases are **COMPLETE and ARCHIVED**. They are not reconstructed, renamed, or re-litigated here.

The active engineering roadmap officially begins at **Phase 5.5**.

---

## Official Roadmap

### Phase 5.5 — Capability Layer

**Status: COMPLETE**

- Skill Metadata
- Capability Discovery
- Metadata-driven Planning

---

### Phase 5.6 — Workspace Memory

**Status: COMPLETE**

- WorkspaceMemory
- WorkspaceMemoryStore
- WorkspaceMemoryManager
- WorkspaceSync
- ContextBuilder Integration
- Runtime Registration

---

### Phase 5.7 — Reflection Engine

**Status: COMPLETE**

- Reflection Architecture
- ReflectionEngine
- Dependency Injection
- BrainCore Integration
- Validation & Freeze

---

### Phase 5.8 — Workspace Activation

**Status: COMPLETE**

- Runtime Activation
- RuntimeFacade Activation API
- Idempotent Activation
- Automatic Workspace Switching
- Validation & Freeze

---

### Phase 5.9 — Workspace Reasoning

**Status: COMPLETE · VALIDATED · FROZEN**

See `Docs/TRUTH/ARCHITECTURE.md` and
`Docs/TRUTH/adr/ADR-0007-workspace-context-boundary.md`.

- Workspace Search
- Decision Recall
- Notes Recall
- Task Recall
- Architecture Recall
- Workspace-aware Planning
- Workspace-aware Prompting
- Project Context Injection
- Validation & Freeze

---

### Phase 6.0 — Evolution Engine

**Status: COMPLETE · VALIDATED · FROZEN**

The Evolution Engine observes and recommends. It never mutates runtime. It
observes execution, measures performance, analyzes outcomes, evaluates
strategies, and produces immutable recommendations and evolution metadata. It
never rewrites BrainCore, the Planner, Workspace, prompts, or skills, and never
changes runtime behavior. Phase 6 is the FOUNDATION for future evolution: it
decides WHAT should evolve. Phase 7 (Skill Creator) consumes Phase 6
recommendations and performs the approved evolution.

Implemented in `backend/brain/evolution/` (all components dormant in DI):

- Reflection Learning — EvolutionObserver, EvolutionObservation, EvolutionStore
- Strategy Improvement — StrategyEvaluator → StrategyAnalysis
- Performance Analysis — PerformanceAnalyzer → PerformanceAnalysis
- Memory Consolidation — MemoryConsolidator → ConsolidationProposalSet
- Self Evolution — RecommendationEngine → EvolutionRecommendationSet
- Validation & Freeze

---

### Phase 7.0 — Skill Creator

**Status: COMPLETE · VALIDATED · FROZEN**

Phase 7 consumes Phase 6 recommendations and performs the approved evolution.
Phase 6 decides WHAT should evolve; Phase 7 performs it. This separation is
permanent.

Implemented as a deterministic 10-stage compiler pipeline in
`backend/brain/skill_creator/` (all stages dormant in DI, one frozen artifact
each). See `Docs/TRUTH/pipeline/01–10` and ADR-0009–0013.

- 7.1 Foundation — contracts (ISkillCreator, SkillBlueprint)
- 7.2 Blueprint Builder → SkillBlueprintSet (+7.2.5/7.2.6/7.2.7 schema harden/freeze/spec)
- 7.3 Verification — BlueprintVerifier → VerificationResult
- 7.4 Generation — BlueprintGenerator → GenerationResult
- 7.5 Testing — BlueprintTester → TestResult
- 7.6 Approval — BlueprintApprover → ApprovalRecord (mandatory human gate)
- 7.7 Installation — BlueprintInstaller → InstallationRecord
- 7.8 Registry — BlueprintRegistry → RegistryEntry (append-only)
- 7.9 Lifecycle — LifecycleManager → LifecycleEvent (append-only)
- 7.10 Marketplace — MarketplacePublisher → MarketplaceManifest
- 7.11 Rollback — RollbackManager → RollbackRecord
- Validation & Freeze

---

### Phase 8.0 — Autonomous Planning

**Status: COMPLETE · VALIDATED · FROZEN**

> **Owner re-scope (2026-07-20, ADR-0014):** Phase 8 is being executed as
> **Skill Runtime** — the consumer of the immutable Phase 7 artifacts (discover,
> match, resolve, sandbox, load, execute installed skills). The heading is
> preserved per Roadmap Governance rule #3 (no rename); the scope below records
> the approved owner directive. Autonomous-planning capabilities are subsumed by
> the runtime's planner-facing services (discovery → matching → chaining).

Skill Runtime milestones:

- **8.1 Registry Discovery — COMPLETE** (`brain/skill_runtime`, dormant).
- **8.2 Capability Matching — COMPLETE** (`brain/skill_runtime`, dormant).
- **8.3 Dependency Resolution — COMPLETE** (`brain/skill_runtime`, dormant).
- **8.4 Skill Sandbox — COMPLETE** (`brain/skill_runtime`, dormant).
- **8.5 Skill Loader — COMPLETE** (`brain/skill_runtime`, dormant).
- **8.6 Skill Executor — COMPLETE** (`brain/skill_runtime`, dormant).
- **8.7 Runtime Context Injection — COMPLETE** (`brain/skill_runtime`, dormant).
- **8.8 Execution Observer — COMPLETE** (`brain/skill_runtime`, dormant; Failure Recovery scope narrowed to observation per ADR-0021).
- **8.9 Execution Recorder — COMPLETE** (`brain/skill_runtime`, dormant; Version Resolution reserved for a later step).
- **8.10 Execution Persistence — COMPLETE** (`brain/skill_runtime`, dormant; prepare-only, storage deferred).
- **8.11 Runtime Pipeline Orchestrator — COMPLETE** (`brain/skill_runtime`, dormant; pure coordinator over stages 11–20, ADR-0024).
- **8.12 Failure Recovery — COMPLETE** (`brain/skill_runtime`, dormant; descriptive `RuntimePipelineResult` → `RecoveryPlan` advisor, decides WHAT without acting, ADR-0025).
- **8.13 Runtime Validation — COMPLETE** (`brain/skill_runtime`, dormant; read-only `RuntimePipelineResult` → `ValidationReport` integrity checker, asserts consistency without repairing, ADR-0026).
- **Validation & Freeze — COMPLETE** (subsystem-wide gate: 13 interfaces/impls, frozen models, AST boundaries, determinism, dormancy; Skill Runtime marked COMPLETE · VALIDATED · FROZEN, ADR-0027).

---

## Roadmap Governance

1. This document is the official engineering roadmap.
2. Phase numbering is frozen.
3. Existing phases may never be renamed.
4. Existing phases may never be reordered.
5. Existing phases may never be merged.
6. Existing phases may never be split.
7. Existing milestones may never move to another phase.
8. New work can only be appended after Phase 8 unless explicitly approved by the project owner.
9. Every implementation milestone must reference one roadmap phase.
10. Architecture discussions must follow this roadmap.
11. Future AI sessions must treat this document as the project's source of truth.
