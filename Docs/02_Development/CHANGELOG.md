# Lumina V2 Changelog

All notable changes to the Lumina V2 platform are documented in this file.

---

## [2.8.freeze] — 2026-07 (Phase 8 — Skill Runtime: Validation & Freeze)

### Validated & Frozen
- **Skill Runtime (Phases 8.1–8.13)** declared **COMPLETE · VALIDATED · FROZEN**.
  Governance gate — no new runtime stage, model, interface, or facade accessor.
- Subsystem-wide validation (`tests/test_phase_8_freeze.py`) asserts, across all
  13 stages at once: all 13 interfaces registered with one impl each + reachable
  via `RuntimeFacade` as shared singletons; every skill_runtime model frozen;
  AST boundary enforcement (no subprocess/threading/asyncio/requests/socket/
  sqlite3; no core.bootstrap/brain.planning/brain.skill_creator imports;
  importlib only in the loader); determinism guard (no clocks/uuid/random/
  secrets in any stage); dormancy (bootstrap registers all, auto-invokes none).
- ADR-0027; pipeline doc `Docs/TRUTH/pipeline/24_validation_and_freeze.md`.

### Note
- Runtime stays dormant and byte-identical; wiring into a live path is a future
  gated decision. Future runtime work appends after Phase 8.

### Unchanged
- Phase 5–8.13 frozen and byte-identical. Regression: **913 PASS** (+9).

---

## [2.8.13] — 2026-07 (Phase 8.13 — Skill Runtime: Runtime Validation)

### Added
- **RuntimeValidator** (`brain/skill_runtime/runtime_validation.py`, impl of
  `IRuntimeValidator`) — first component that asserts a pipeline result's
  structural integrity. Consumes a `RuntimePipelineResult` and returns an
  immutable `ValidationReport` of invariant violations: (1) contiguity — the
  populated stages form a gap-free prefix; (2) completion — `completed` iff all
  ten stages populated AND `reason` empty; (3) reason match — a failed `reason`
  matches the last populated stage (fixed stop-reason table). Read-only —
  checks and reports, never repairs/re-runs/mutates/executes/recovers.
  Deterministic (fixed stage-order + reason table; no clocks/ids/entropy/IO).
  Dormant in DI.
- `ValidationReport` (frozen model); `IRuntimeValidator` contract.
- `RuntimeFacade.runtime_validator`; `bootstrap._register_runtime_validator`.
- Pipeline doc `Docs/TRUTH/pipeline/23_runtime_validation.md`; ADR-0026.

### Note
- Nothing calls it automatically; acting on a `ValidationReport` is a future
  gated decision.

### Unchanged
- Phase 5–8.12 frozen and byte-identical. Regression: **904 PASS** (+15).

---

## [2.8.12] — 2026-07 (Phase 8.12 — Skill Runtime: Failure Recovery)

### Added
- **FailureRecovery** (`brain/skill_runtime/failure_recovery.py`, impl of
  `IFailureRecovery`) — first component that reasons about a failed pipeline run.
  Consumes a `RuntimePipelineResult` and returns an immutable `RecoveryPlan`
  naming WHAT recovery should happen (strategy from a closed vocabulary:
  `none`/`retry_transient`/`rematch_capability`/`review_required`/`abort`, a
  `retryable` flag, a `rationale`). Descriptive only — mirrors the Evolution
  Engine: decides WHAT, performs nothing. Never retries, re-invokes, executes,
  loads, loops, or mutates. Deterministic (fixed reason→strategy table; no
  clocks/ids/entropy/IO). Dormant in DI.
- `RecoveryPlan` (frozen model); `IFailureRecovery` contract.
- `RuntimeFacade.failure_recovery`; `bootstrap._register_failure_recovery`.
- Pipeline doc `Docs/TRUTH/pipeline/22_failure_recovery.md`; ADR-0025.

### Note
- Nothing calls it automatically; acting on a `RecoveryPlan` is a future gated
  decision.

### Unchanged
- Phase 5–7 frozen and byte-identical; Phase 8.11 orchestrator untouched.
  Regression: **889 PASS** (+11).

---

## [2.8.11] — 2026-07 (Phase 8.11 — Skill Runtime: Runtime Pipeline Orchestrator)

### Added
- **RuntimePipeline** (`brain/skill_runtime/runtime_pipeline.py`, impl of
  `IRuntimePipeline`) — first component that understands the full runtime chain.
  Coordinates the ten stages (discovery → matching → resolution → sandbox →
  loader → context injection → executor → observer → recorder → persistence) in
  order, feeding each the previous stage's output; returns an immutable
  `RuntimePipelineResult` carrying every completed artifact + a `reason`.
  Fail-fast (stops + propagates reason on first failing stage; `execution_failed`
  still runs the observer→recorder→persistence tail). Pure coordinator — no
  business logic, no mutation, no IO/clocks/retries. Stage services
  constructor-injected (interfaces only). Dormant in DI.
- `RuntimeFacade.runtime_pipeline`; `bootstrap._register_runtime_pipeline`.
- Pipeline doc `Docs/TRUTH/pipeline/21_runtime_pipeline.md`; ADR-0024.

### Note
- Nothing calls it automatically; wiring into a real runtime path is future work.

### Unchanged
- Phase 5–7 frozen and byte-identical. Regression: **878 PASS** (+14).

---

## [2.8.10] — 2026-07 (Phase 8.10 — Skill Runtime: Execution Persistence)

### Added
- **ExecutionPersistence** (`brain/skill_runtime/execution_persistence.py`, impl
  of `IExecutionPersistence`) — prepare step (NOT storage): `ExecutionRecord` →
  immutable `PersistenceResult`. Decides persistability + wraps the record with a
  caller-supplied `storage_key`. Stores nothing; no IO/serialization. Depends
  only on the record. Deterministic. Dormant in DI.
- `RuntimeFacade.execution_persistence`; `bootstrap._register_execution_persistence`.
- Pipeline doc `Docs/TRUTH/pipeline/20_execution_persistence.md`; ADR-0023.

### Note
- Actual storage (disk/db/vector) is a future phase — this stage only prepares.

### Unchanged
- Phase 5–7 frozen and byte-identical. Regression: **864 PASS** (+14).

---

## [2.8.9] — 2026-07 (Phase 8.9 — Skill Runtime: Execution Recorder)

### Added
- **ExecutionRecorder** (`brain/skill_runtime/execution_recorder.py`, impl of
  `IExecutionRecorder`) — pure transformation: `ExecutionObservation` →
  persistence-ready immutable `ExecutionRecord`. Does NOT persist/log/save/learn.
  Depends only on the observation. Deterministic (metadata deep-copied; timestamp
  caller-supplied). Dormant in DI.
- `RuntimeFacade.execution_recorder`; `bootstrap._register_execution_recorder`.
- Pipeline doc `Docs/TRUTH/pipeline/19_execution_recorder.md`; ADR-0022.

### Unchanged
- Phase 5–7 frozen and byte-identical. Regression: **850 PASS** (+17).

---

## [2.8.8] — 2026-07 (Phase 8.8 — Skill Runtime: Execution Observer)

### Added
- **ExecutionObserver** (`brain/skill_runtime/execution_observer.py`, impl of
  `IExecutionObserver`) — purely observational: `ExecutionResult` →
  immutable `ExecutionObservation` (registry_key, succeeded, error, output_type,
  timestamp, summary). Never executes/retries/mutates/logs/touches disk. Depends
  only on ExecutionResult. Deterministic (timestamp caller-supplied). Dormant.
- `RuntimeFacade.execution_observer`; `bootstrap._register_execution_observer`.
- Pipeline doc `Docs/TRUTH/pipeline/18_execution_observer.md`; ADR-0021.

### Unchanged
- Phase 5–7 frozen and byte-identical. Regression: **833 PASS** (+16).

---

## [2.8.7] — 2026-07 (Phase 8.7 — Skill Runtime: Context Injection)

### Added
- **ContextInjector** (`brain/skill_runtime/context_injector.py`, impl of
  `IContextInjector`) — pure transformation: `LoadedSkill` + caller data →
  immutable `ExecutionContext` (frozen primitives; no live services/runtime
  objects/raw instance). Returns `ContextInjectionResult`. Never loads/executes/
  accesses registry/writes memory. Inputs never mutated (dicts copied). Dormant.
- Models `ExecutionContext`, `ContextInjectionResult`.
- `RuntimeFacade.context_injector`; `bootstrap._register_context_injector`.
- Pipeline doc `Docs/TRUTH/pipeline/17_context_injection.md`; ADR-0020.

### Unchanged
- Phase 5–7 frozen and byte-identical. Regression: **817 PASS** (+15).

---

## [2.8.6] — 2026-07 (Phase 8.6 — Skill Runtime: Skill Executor)

### Added
- **SkillExecutor** (`brain/skill_runtime/skill_executor.py`, impl of `ISkillExecutor`)
  — runs a `LoadedSkill` exactly once via canonical `run(context)`; captures the
  outcome as immutable `ExecutionResult`. Never retries/recovers/chains; never
  lets an exception propagate. Depends only on Phase 8.5 output. Dormant in DI.
- **Canonical runtime interface** standardized to `run(context)`; legacy
  `execute()` accepted via a minimal shim (loader reports canonical "run").
- `RuntimeFacade.skill_executor`; `bootstrap._register_skill_executor`.
- Pipeline doc `Docs/TRUTH/pipeline/16_skill_executor.md`; ADR-0019.

### Changed
- SkillLoader (8.5) entrypoint validation narrowed to canonical `run` (+legacy
  `execute` fallback); reported entrypoint is always "run". No behavioral break.

### Unchanged
- Phase 5–7 frozen and byte-identical. Regression: **802 PASS** (+17, +refined 8.5).

---

## [2.8.5] — 2026-07 (Phase 8.5 — Skill Runtime: Skill Loader)

### Added
- **SkillLoader** (`brain/skill_runtime/skill_loader.py`, impl of `ISkillLoader`)
  — turns an approved `SandboxDecision` into a loaded, validated skill instance:
  locate `<installed_location>/skill.py` → import (importlib, by path) →
  instantiate `Skill` → validate `execute`/`run` entrypoint → immutable
  `LoadedSkill`. Never executes. Depends only on Phase 8.4 output. Dormant in DI.
  - Failure-safe: locate/import/instantiate/validate errors → loaded=False +
    descriptive error; never raises. No eval/exec/compile/subprocess.
- `RuntimeFacade.skill_loader`; `bootstrap._register_skill_loader`.
- Pipeline doc `Docs/TRUTH/pipeline/15_skill_loader.md`; ADR-0018.

### Unchanged
- Phase 5–7 frozen and byte-identical. Regression: **785 PASS** (+16).

---

## [2.8.4] — 2026-07 (Phase 8.4 — Skill Runtime: Skill Sandbox)

### Added
- **SkillSandbox** (`brain/skill_runtime/skill_sandbox.py`, impl of `ISkillSandbox`)
  — first runtime execution-safety layer. Pure allow/deny gatekeeper over a
  `DependencyResolution` + `SandboxPolicy`; returns immutable `SandboxDecision`.
  Never loads/imports/executes. Depends only on Phase 8.3 output. Dormant in DI.
  - Checks: resolved (require_resolved), skill present, permission ∈ allowlist,
    no unsatisfied requirement.
- `RuntimeFacade.skill_sandbox`; `bootstrap._register_skill_sandbox`.
- Pipeline doc `Docs/TRUTH/pipeline/14_skill_sandbox.md`; ADR-0017.

### Note
- `policy.max_risk` informational; execution-time permission enforcement → 8.6.
  Frozen `RegistryEntry` projection carries no risk field (ADR-0017).

### Unchanged
- Phase 5–7 frozen and byte-identical. Regression: **769 PASS** (+16).

---

## [2.8.3] — 2026-07 (Phase 8.3 — Skill Runtime: Dependency Resolution)

### Added
- **DependencyResolver** (`brain/skill_runtime/dependency_resolver.py`, impl of
  `IDependencyResolver`) — gate between matching and loading. Selects the
  top-ranked match whose dependencies are satisfied; returns immutable
  `DependencyResolution` (with `DependencyRequirement` checklist). Dormant in DI.
  - Depends only on Phase 8.2 `CapabilityMatchResult` + supplied grants; no
    Registry / RegistryEntry / skill_creator import. Pure + deterministic.
  - Checks registration, install, capability restriction; records runtime
    version + permission grants.
- `RuntimeFacade.dependency_resolver`; `bootstrap._register_dependency_resolver`.
- Pipeline doc `Docs/TRUTH/pipeline/13_dependency_resolution.md`; ADR-0016.

### Note
- Permission enforcement deferred to 8.4 (Sandbox); version constraints to 8.9 —
  frozen `RegistryEntry` projection carries neither (ADR-0016).

### Unchanged
- Phase 5–7 frozen and byte-identical. Regression: **753 PASS** (+19).

---

## [2.8.2] — 2026-07 (Phase 8.2 — Skill Runtime: Capability Matching)

### Added
- **CapabilityMatcher** (`brain/skill_runtime/capability_matcher.py`, impl of
  `ICapabilityMatcher`) — semantic layer over Registry Discovery. Answers "which
  skills satisfy this capability?" so the Planner asks the matcher, not the
  registry. Dormant in DI; no runtime consumer yet.
  - Immutable models `CapabilityRequest`, `CapabilityMatch`, `CapabilityMatchResult`.
  - Depends ONLY on `IRegistryDiscovery`; no Registry / RegistryEntry /
    skill_creator import. Pure + deterministic (no I/O, clocks, entropy).
  - Scoring: exact capability 100 / alias 80 / tag 60; family+package hard
    filters; order score desc, family, package, registry_key.
- `RuntimeFacade.capability_matcher`; `bootstrap._register_capability_matcher`.
- Pipeline doc `Docs/TRUTH/pipeline/12_capability_matching.md`; ADR-0015.

### Note
- `version_preference` is inert — frozen Phase 7 `RegistryEntry` carries no
  version; deferred to Phase 8.9 (ADR-0015).

### Unchanged
- Phase 5–7 frozen and byte-identical. Regression: **734 PASS** (+21).

---

## [2.8.1] — 2026-07 (Phase 8.1 — Skill Runtime: Registry Discovery)

### Added
- **Skill Runtime (`brain/skill_runtime/`)** — first runtime consumer of the
  frozen Phase 7 registry. `RegistryDiscovery` (impl of `IRegistryDiscovery`)
  answers "what skills exist?" so the Planner discovers skills via DI instead of
  importing them. Dormant in DI; no runtime path wires into it yet.
  - Immutable outputs `DiscoveredSkill` (read-only projection of a `RegistryEntry`,
    metadata-only) and `RegistrySearchResult`.
  - Read-only, deterministic; duck-typed over the registry (only `.entries()`),
    so no import of `BlueprintRegistry` and no upward Phase-7 dependency.
  - Supersession without mutation (latest-per-key wins), registered-only
    visibility, stable ordering `(family, package, key)`.
- `RuntimeFacade.registry_discovery` accessor; `bootstrap._register_skill_runtime`.
- Pipeline doc `Docs/TRUTH/pipeline/11_runtime_discovery.md`; ADR-0014.

### Unchanged
- Phase 5–7 frozen and byte-identical. Runtime behaviour unchanged (dormant).
- Regression: **713 PASS** (was 694; +19 Phase 8.1).

---

## [2.7.0] — 2026-07 (Phase 7 — Skill Creator, frozen)

### Added
- **Skill Creator (`brain/skill_creator/`)** — deterministic 10-stage compiler
  pipeline, all stages dormant in DI, one frozen artifact each (ADR-0009–0013).
  - Builder → Verifier → Generator → Tester → Approver (human gate) → Installer
    → Registry (append-only) → Lifecycle (append-only) → Marketplace → Rollback.
  - Artifacts: SkillBlueprint(Set), VerificationResult, GenerationResult,
    TestResult, ApprovalRecord, InstallationRecord, RegistryEntry, LifecycleEvent,
    MarketplaceManifest, RollbackRecord.
- Pipeline docs `Docs/TRUTH/pipeline/01–10`; ADR-0009 (pipeline), ADR-0010
  (compiler-pipeline law), ADR-0011 (blueprint schema frozen), ADR-0012 (artifact
  immutability), ADR-0013 (SkillArtifactBundle reservation).

### Notes
- No runtime consumer yet (Phase 8, Skill Runtime). Runtime byte-identical.
- Full regression: **694 passing** (214 Phase 7).

---

## [2.6.0] — 2026-07 (Phase 6 — Evolution Engine, frozen)

### Added
- **Evolution Engine (`brain/evolution/`)** — analysis-only, fully dormant (ADR-0008).
  Registered in DI but consumed by no runtime path; runtime byte-identical.
  - **6.1** `EvolutionObserver` + `EvolutionObservation` + append-only `EvolutionStore`.
  - **6.2** `StrategyEvaluator` → `StrategyAnalysis`.
  - **6.3** `PerformanceAnalyzer` → `PerformanceAnalysis`.
  - **6.4** `MemoryConsolidator` → `ConsolidationProposalSet` (read-only proposals).
  - **6.5** `RecommendationEngine` → `EvolutionRecommendationSet`.
  - **6.6** Validation & Freeze.
- **ADR-0008** — Evolution Engine boundary (analysis layer, never mutates runtime).

### Notes
- All evolution models frozen + serializable; ids deterministic (no UUID/time/random).
- Full Phase 5 + Phase 6 regression: 480 passing.

---

## [2.5.0] — 2026-07 (Phase 5 — Cognitive Architecture, frozen)

### Added
- **BrainCore** orchestrator + frozen value objects (5.1).
- **Planning & Skills** — RulePlanner, LLMPlanner, PlannerChain, SkillManager (5.2–5.3).
- **Capability Layer** — skill metadata + capability discovery (5.5).
- **Workspace Memory** — memory/store/manager/sync + ContextBuilder read (5.6).
- **Reflection Engine** — deterministic, read-only, attached by BrainCore (5.7).
- **Workspace Activation** — `RuntimeFacade.activate_workspace`, idempotent, flag-gated (5.8).
- **Workspace Reasoning** — WorkspaceRetriever; Decision/Notes/Task/Architecture
  recall; workspace-aware planning + prompting; project context injection (5.9).
- **ADR-0007** — Workspace context boundary (`PromptWorkspaceContext` is the only
  object crossing into prompt generation).

---

## [2.2.0] — 2026-07 (Phase 4 final)

### Added
- Created a FastAPI route `GET /debug/events` to return the live EventBus subscription table as a JSON payload for diagnostics.
- Added `Docs/ARCHITECTURE.md` as the authoritative runtime and structural reference.

### Fixed
- **Legacy Path Elimination**: Completely removed the `_get_memory_store()` function and the `_fallback_memory_store` global in `server.py`. Migrated all 15 call-sites to `_svc.memory_store`, eliminating the last legacy path that bypassed the DI container.
- Added `None` safety guards in all panel CRUD Socket handlers to prevent crashes if events trigger before the AudioLoop session attaches.

---

## [2.1.0] — 2026-07 (Phase 4 launch)

### Added
- **FastAPI Port Recovery**: Added `find_available_port()` to uvicorn startup. Scans ports 8000–8009 and falls back dynamically if port 8000 is occupied, updating the dashboard routes.
- **Graceful Shutdown**: Added FastAPI shutdown handlers to publish `session.shutdown` to EventBus on exit.
- **Settings Validation & Self-Healing**: Created a Pydantic `SettingsSchema` model covering all parameters (VAD timers, smart home kasa devices, personas). Added `validate_and_repair_settings()` to heal corrupted configs automatically.
- **Event-Driven Remote Control**: Refactored paired mobile dashboard routes to stream audio chunks and dispatch commands over the `InProcessEventBus` (`dashboard.connected`, `dashboard.command`, `dashboard.wake`, `dashboard.audio`).
- **Adjustable VAD Timers**: Added configurable VAD variables (`vad_min_speech_ms`, `vad_silence_stop_ms` set to 900ms, `vad_pre_roll_ms`, `vad_post_roll_ms`) in settings to prevent first/last word clipping.
- **DEBUG_AUDIO Flag**: Verbose VAD log prints are now gated behind `DEBUG_AUDIO` to reduce log spam and prevent audio playbacks from stuttering.

---

## [2.0.0] — 2026-07 (Interface Refactor)

### Added
- **Dependency Injection Container**: Dynamic service container in `container.py` and `bootstrap.py` for registering core managers (`IBrainState`, `IEventBus`, `IMemoryManager`, `IWorkspaceManager`).
- **SessionManager**: Governs active AudioLoop lifecycle references, replacing module-level globals in `server.py`.
- **ServiceAccessor**: lookup bridge to resolve from the DI container with passive fallbacks.
- **ExecutionContext**: Context tracing schemas per request.
- **RequestPipeline**: Request execution middlewares.

---

## [1.1.0] — 2026-02 (Phase B/C/D Refactors)

### Added
- **Windows Unicode Fix**: Changed Unicode checkmarks (`✓`) in startup prints to ASCII text (`OK`) to prevent `UnicodeEncodeError` crashes on Windows terminals.
- **Safe PID Cleanup**: Added tasklist existence checks in Electron's `main.js` before calling `taskkill` to prevent launcher crashes during process exit.
- **Chat UI command results**: Frontend chat UI now listens to `chat_message` events to display output from `/memory` and `/remember` commands.
- **Identity Seeding**: Added `_seed_owner_identity()` to idempotently seed user preferences and name facts on startup.
- **Tool Socket Guards**: Added guards to `discover_kasa`, `discover_printers`, `print_stl`, and `control_kasa` Socket handlers to return empty structures without crashes when tools are disabled.
