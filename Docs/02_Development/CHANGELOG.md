# Lumina V2 Changelog

All notable changes to the Lumina V2 platform are documented in this file.

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
