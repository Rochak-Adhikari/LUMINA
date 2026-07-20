# Lumina V2 Current Status

This document defines the current release status, active development phase, and known technical debt of the Lumina V2 platform.

---

## 1. Release Metadata

- **Current Version**: 2.7.0 (Cognitive Architecture + Evolution Engine + Skill Creator)
- **Active Development Phase**: Phase 7 complete; Phase 8 (Skill Runtime) not started
- **Architectural Status**: Runtime core FROZEN; Phase 5, 6 & 7 FROZEN
- **Last Updated**: July 2026

---

## 2. Completed Phases

Foundational runtime (Phases 1–4), the Cognitive Architecture (Phase 5),
Evolution Engine (Phase 6), and Skill Creator (Phase 7) are complete. See
`Docs/02_Development/PHASE_HISTORY.md` for details and
`Docs/04_Guides/FEATURE_GUIDE.md` for how every feature works.

### Phases 1–4 — Runtime Foundation ✅
- DI container, `BrainState`, `InProcessEventBus`, `RequestPipeline`,
  `RuntimeFacade`; state migrations; `SessionManager`/`ServiceAccessor`;
  stable runtime recovery (port scan, graceful shutdown, settings self-heal).

### Phase 5 — Cognitive Architecture ✅ (FROZEN)
- **5.1** BrainCore orchestrator + frozen value objects.
- **5.2–5.3** RulePlanner, LLMPlanner, PlannerChain, SkillManager/Registry.
- **5.5** Capability Layer (skill metadata, capability discovery).
- **5.6** Workspace Memory (memory/store/manager/sync + ContextBuilder read).
- **5.7** Reflection Engine (deterministic, read-only, attached by BrainCore).
- **5.8** Workspace Activation (`RuntimeFacade.activate_workspace`, idempotent,
  flag-gated).
- **5.9** Workspace Reasoning: WorkspaceRetriever; Decision/Notes/Task/
  Architecture recall; workspace-aware planning; workspace-aware prompting;
  project context injection (ADR-0007 boundary).

### Phase 6 — Evolution Engine ✅ (VALIDATED · FROZEN)
Analysis-only, fully dormant (ADR-0008). Observe → aggregate → measure →
consolidate → recommend:
- **6.1** EvolutionObserver + EvolutionObservation + append-only EvolutionStore.
- **6.2** StrategyEvaluator → StrategyAnalysis.
- **6.3** PerformanceAnalyzer → PerformanceAnalysis.
- **6.4** MemoryConsolidator → ConsolidationProposalSet (read-only proposals).
- **6.5** RecommendationEngine → EvolutionRecommendationSet.
- **6.6** Validation & Freeze.

### Phase 7 — Skill Creator ✅ (VALIDATED · FROZEN)
Deterministic 10-stage compiler pipeline in `backend/brain/skill_creator/`; each
stage a dormant DI-registered class producing one frozen artifact. See
`Docs/TRUTH/pipeline/01–10` + ADR-0009–0013.
- **7.1** Foundation (contracts) · **7.2** Blueprint Builder (+7.2.5/7.2.6/7.2.7 schema harden/freeze/spec)
- **7.3** Verification · **7.4** Generation · **7.5** Testing
- **7.6** Approval (human gate) · **7.7** Installation · **7.8** Registry (append-only)
- **7.9** Lifecycle (append-only) · **7.10** Marketplace · **7.11** Rollback

---

## 3. Current & Next Phases

### Current: Phase 7 frozen
Runtime core stable and frozen. Skill Creator pipeline registered but dormant —
no runtime path consumes it; runtime behavior byte-identical to Phase 5. Full
Phase 5 + 6 + 7 regression passing (**694 tests**; 214 Phase 7).

### Next: Phase 8 — Skill Runtime (Planned)
The runtime that USES skills created by the pipeline — consumes `RegistryEntry`
and runtime requests to discover, validate, sandbox, load, and execute installed
skills. Will not modify the frozen Skill Creator pipeline.

---

## 4. Known Technical Debt

1. **Global Module-Level States**: `server.py` contains several global variables (`last_user_activity`, `connected_clients`, `idle_disabled_until_ts`) mutated directly across async event tasks without locks.
2. **Lockless Logging**: `ProjectManager` writes chat logs to `chat_history.jsonl` using a simple `open()` without thread locks, risking lockups under rapid inputs.
3. **Duck-Typing Registrations**: `ProjectManager` and `MemoryStore` do not inherit from `IWorkspaceManager` and `IMemoryManager` directly; they are virtually mapped during startup bootstrap.
4. **`cv2` Import Spec**: Camera frames use `cv2.CAP_DSHOW` on Windows, but the MediaPipe landmark task relies on static asset placement (`face_landmarker.task`) which is currently hardcoded relative to the backend root.
