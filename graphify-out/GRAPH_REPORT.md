# Graph Report - .  (2026-07-21)

## Corpus Check
- 337 files · ~231,678 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4753 nodes · 11026 edges · 207 communities (174 shown, 33 thin omitted)
- Extraction: 69% EXTRACTED · 31% INFERRED · 0% AMBIGUOUS · INFERRED: 3449 edges (avg confidence: 0.65)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Infrastructure Adapters & App Host
- BrainCore Orchestrator
- Rule Planner & Skill Seeding
- Reminders & Task Scheduler
- Planner Contracts & BrainContext
- CMD/Shell Control
- Skill Runtime Persistence
- Dev Agent / Package Generator
- Browser Open & CDP
- Memory Engine & Embeddings
- Legacy Session Dispatch
- Context Builder
- Socket.IO Server
- DI Container Resolvers
- Runtime Pipeline Orchestrator
- Workspace Memory
- Workspace Memory Manager
- Session Lifecycle
- Frontend UI Components
- Game Updater
- Workspace Retriever
- AudioLoop / Gemini Live
- Web Agent Tests
- Capability Matching
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 170
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Community 178
- Community 179
- Community 180
- Community 181
- Community 182
- Community 183
- Community 184
- Community 185
- Community 186
- Community 187
- Community 188
- Community 189
- Community 190
- Community 191
- Community 192
- Community 193
- Community 194
- Community 195
- Community 196
- Community 197
- Community 198
- Community 200

## God Nodes (most connected - your core abstractions)
1. `Bootstrapper` - 339 edges
2. `DependencyContainer` - 291 edges
3. `RuntimeFacade` - 213 edges
4. `BrainRequest` - 136 edges
5. `SkillRegistry` - 99 edges
6. `ContextBuilder` - 90 edges
7. `BlueprintBuilder` - 89 edges
8. `WorkspaceMemory` - 89 edges
9. `BlueprintVerifier` - 85 edges
10. `BlueprintGenerator` - 73 edges

## Surprising Connections (you probably didn't know these)
- `lumina conda environment` --conceptually_related_to--> `Lumina`  [INFERRED]
  backend/requirements-dev.txt → backend/documents/Version 3.5 for Lumina.txt
- `TranscriptAggregator` --uses--> `ActionRouter`  [INFERRED]
  backend/server.py → backend/action_router.py
- `user_input()` --calls--> `ActionRouter`  [INFERRED]
  backend/server.py → backend/action_router.py
- `WhatsAppMessage` --uses--> `ActionRouter`  [INFERRED]
  backend/server.py → backend/action_router.py
- `_detect_action()` --calls--> `get_genai_model()`  [INFERRED]
  backend/actions/computer_settings.py → backend/actions/_gemini_helper.py

## Import Cycles
- None detected.

## Communities (207 total, 33 thin omitted)

### Community 0 - "Infrastructure Adapters & App Host"
Cohesion: 0.02
Nodes (102): core/adapters.py — Lumina V2 Infrastructure Adapters (Phase 1.6)  Thin pass-th, ApplicationHost, core/application.py — Lumina V2 Application Lifecycle Layer (Phase 1.3, 4.5), Owns the application lifecycle: initialize → start → stop → dispose.      Each, Phase 4.5: Register an async cleanup hook to be called during stop().         H, Run the bootstrapper to construct and register all services., Mark the application as running. Requires initialize() first., Phase 4.5: Unified graceful shutdown — coordinates cleanup across         all r (+94 more)

### Community 1 - "BrainCore Orchestrator"
Cohesion: 0.03
Nodes (75): BrainCore, Any, brain/core/brain_core.py — BrainCore orchestrator (Phase 5.4 Step 4)  The single, Produce a Reflection for a completed request; never raise. Read-only.         Re, Best-effort event publish — never breaks the pipeline., Cognitive orchestrator.      Collaborators (all injected):       context_builder, Process one BrainRequest (see module docstring for handled semantics)., IBrainCore (+67 more)

### Community 2 - "Rule Planner & Skill Seeding"
Cohesion: 0.03
Nodes (47): brain/planning/rule_planner.py — Phase 5.2 RulePlanner (Phase 5.4 Step 1: contra, Deterministic pattern-based planner., RulePlanner, brain/skills/builtin.py — Skill metadata seed (Phase 5.4 Step 0: truth-aligned), Register all builtin SkillSpecs. Returns count registered., seed_registry(), LegacyToolExecutor, Any (+39 more)

### Community 3 - "Reminders & Task Scheduler"
Cohesion: 0.06
Nodes (42): _create_windows_task(), _delete_windows_task(), _list_windows_tasks(), _parse_natural_time(), _platform_not_supported(), Parse natural language time/date expressions.     Examples: '5 minutes', 'tomor, Lumina system-level reminder (Windows Task Scheduler).      parameters:, Creates a Windows Task Scheduler one-shot task that shows a msgbox. (+34 more)

### Community 4 - "Planner Contracts & BrainContext"
Cohesion: 0.05
Nodes (35): IPlanner, Produces a Plan from a BrainContext — or None when the request is not     recogn, Return a Plan for *context*, or None if not recognized., BrainContext, Everything BrainCore assembled for one request: the request itself plus     read, _await(), _extract_json(), LLMPlanner (+27 more)

### Community 5 - "CMD/Shell Control"
Cohesion: 0.05
Nodes (70): _ask_gemini(), cmd_control(), _find_hardcoded(), _get_platform(), _is_safe(), Lumina CMD / Shell control action.      parameters:         task    : Natural, Use Gemini to convert a natural language task to a CMD command., _run_silent() (+62 more)

### Community 6 - "Skill Runtime Persistence"
Cohesion: 0.05
Nodes (29): ExecutionPersistence, brain/skill_runtime/execution_persistence.py — Phase 8.10: ExecutionPersistence, Deterministic, pure persistence-prepare step. Stores nothing., ExecutionRecorder, Any, brain/skill_runtime/execution_recorder.py — Phase 8.9: ExecutionRecorder  Pure t, Deterministic, pure observation→record transformer. No persistence., IExecutionPersistence (+21 more)

### Community 7 - "Dev Agent / Package Generator"
Cohesion: 0.05
Nodes (41): Deterministic filesystem-safe directory name for a package., _safe_dirname(), BlueprintTester, brain/skill_creator/blueprint_tester.py — Phase 7.5: BlueprintTester  Pipeline s, Deterministic static tester of a generated skill package., Record an explicit human approval decision over *test_result*., Materialize the approved generated package under *target_root*., Append a RegistryEntry for an installed skill; return that entry. (+33 more)

### Community 8 - "Browser Open & CDP"
Cohesion: 0.06
Nodes (58): browser_open(), _cdp_reachable(), _ensure_lumina_dirs(), _is_likely_media_tab(), _open_in_lumina_browser(), actions/browser_open.py — Lumina dedicated browser open tool  Opens URLs or kn, Create dedicated profile/downloads dirs if they don't exist., Check if Lumina's dedicated browser CDP port is responding. (+50 more)

### Community 9 - "Memory Engine & Embeddings"
Cohesion: 0.05
Nodes (26): chunk_text(), EmbeddingProvider, hash_chunk(), MemoryEngine, Lumina Memory Engine v2 — Hybrid Retrieval (Keyword + Vector)  Inspired by Ope, Text embedding via Google Gemini (primary) or deterministic hash fallback., Embed a list of texts. Returns list of numpy float32 arrays (or None on per-item, Nearest-neighbour search over chunk embeddings. (+18 more)

### Community 10 - "Legacy Session Dispatch"
Cohesion: 0.06
Nodes (25): build_session_dispatch(), Any, Exception, core/legacy_dispatch.py — Phase 5.4 Step 3 (Order 6): session dispatch closure, Permission gate denied the tool (explicitly disabled)., Tool would require user confirmation; the Brain path refuses it in 5.4., The bound session is no longer live (D7 stale-loop guard)., Build an async dispatch closure bound to *audio_loop*.      The returned callabl (+17 more)

### Community 11 - "Context Builder"
Cohesion: 0.06
Nodes (22): ContextBuilder, Any, brain/core/context_builder.py — ContextBuilder (Phase 5.6.5: workspace enrichmen, Prepare read-only workspace recall for the planner (Phase 5.9.7).          Deriv, Delegate to one recall service; empty result on absence/failure., Read-only assembler of BrainContext.      Collaborators are injected and all opt, Return a frozen BrainContext for *request*., Extract a small read-only dict from BrainState.snapshot().          Uses get_sta (+14 more)

### Community 12 - "Socket.IO Server"
Cohesion: 0.04
Nodes (40): add_memory(), connect(), get_memories(), get_memory_stats(), hb_pong(), heartbeat_loop(), idle_timer_loop(), is_port_free() (+32 more)

### Community 13 - "DI Container Resolvers"
Cohesion: 0.04
Nodes (28): Any, Resolve the registered ApplicationHost for unified lifecycle., Resolve the registered IBrainCore (BrainCore skeleton).          Resolved dire, Resolve the registered IPlanner (Phase 5.4 Step 8: PlannerChain)., Resolve the registered SkillRegistry (Phase 5.2)., Resolve the registered SkillManager (Phase 5.2)., Resolve the registered LLMPlanner (Phase 5.3; inert until a         model gatew, Resolve the registered PlannerChain (Phase 5.3:         RulePlanner -> LLMPlann (+20 more)

### Community 14 - "Runtime Pipeline Orchestrator"
Cohesion: 0.07
Nodes (22): brain/skill_runtime/runtime_pipeline.py — Phase 8.11: Runtime Pipeline Orchestra, Coordinator over the ten runtime stages. Holds no business logic., RuntimePipeline, _Calls, _Discovery, _Executor, _Injector, _Loader (+14 more)

### Community 15 - "Workspace Memory"
Cohesion: 0.08
Nodes (17): brain/workspace/memory.py — Phase 5.6.2: in-memory WorkspaceMemory  Pure in-memo, In-memory structured project memory for a single workspace., WorkspaceMemory, Decision, ProjectInfo, High-level description of the project a workspace represents., A recorded implementation / design decision., tests/test_phase_5_6_step2.py — Phase 5.6.2: WorkspaceMemory (in-memory)  Pure i (+9 more)

### Community 17 - "Workspace Memory Manager"
Cohesion: 0.06
Nodes (18): Path, brain/workspace/manager.py — Phase 5.6.4: WorkspaceMemoryManager  Runtime owner, Coordinates the active WorkspaceMemory via a store. No globals., Return the currently-active WorkspaceMemory (empty until switch)., Persist the current WorkspaceMemory to *workspace_path* via the store., Load the WorkspaceMemory for *workspace_path* via the store and make         it, Reset the current WorkspaceMemory to an empty in-memory instance., WorkspaceMemoryManager (+10 more)

### Community 18 - "Session Lifecycle"
Cohesion: 0.05
Nodes (22): Any, core/session.py — Lumina V2 Session Lifecycle Manager (Phase 3)  Centralizes o, Return the current AudioLoop instance, or None if not attached.          Threa, True if an AudioLoop is currently attached., Return the asyncio.Task running AudioLoop.run(), or None., Store (or clear, with None) the asyncio.Task running AudioLoop.run()., Return the FaceAuthenticator instance, or None., Store (or clear, with None) the FaceAuthenticator reference. (+14 more)

### Community 19 - "Frontend UI Components"
Cohesion: 0.12
Nodes (25): MessageInput(), SIZES, VARIANTS, Dialog(), GlassCard(), SearchBox(), Select(), SettingCard() (+17 more)

### Community 20 - "Game Updater"
Cohesion: 0.14
Nodes (44): _cancel_scheduled_update(), _click_button(), _click_first_profile_by_screenshot(), _ensure_steam_running(), _epic_manifests_path(), _find_best_drive(), _find_epic_exe(), _find_epic_exe_linux() (+36 more)

### Community 21 - "Workspace Retriever"
Cohesion: 0.07
Nodes (16): IWorkspaceRetriever, Read-only retrieval contract over the active WorkspaceMemory (Phase 5.9.1)., Any, brain/workspace/retriever.py — Phase 5.9.1: WorkspaceRetriever  Deterministic, R, Read-only, deterministic retriever over the active WorkspaceMemory., Return records matching *query* and optional filters.          - ``query``: matc, WorkspaceRetriever, _FakeManager (+8 more)

### Community 22 - "AudioLoop / Gemini Live"
Cohesion: 0.06
Nodes (13): Return the Gemini session from the active AudioLoop, or None., AudioLoop, Seed core identity facts about owner.         Idempotent - only adds if not alr, Forward phone mic PCM chunks from dashboard queue into the Gemini Live session., Forces the current chat buffer to be written to log., Clears the queue of pending audio chunks to stop playback immediately., Send to Gemini session, waiting for any active turn to finish first.         On, Background task to reads from the websocket and write pcm chunks to the output q (+5 more)

### Community 23 - "Web Agent Tests"
Cohesion: 0.06
Nodes (27): Tests for Web Automation Agent., Test screenshot capabilities., Test capturing a screenshot., Test WebAgent initialization., Test full web agent task execution., Test running a simple web task., Test WebAgent can be created., Test Playwright availability. (+19 more)

### Community 24 - "Capability Matching"
Cohesion: 0.08
Nodes (26): Select the highest-ranked match whose dependencies are all satisfied and, CapabilityMatch, CapabilityMatchResult, DependencyRequirement, DependencyResolution, DiscoveredSkill, ExecutionContext, BaseModel (+18 more)

### Community 25 - "Community 25"
Cohesion: 0.10
Nodes (16): EvolutionObservation, Immutable record of one observed Reflection (Phase 6.1).      Deterministic: bui, EvolutionObserver, Any, brain/evolution/observer.py — Phase 6.1: EvolutionObserver  The observation entr, Observes Reflection → stores EvolutionObservation. No runtime effect., Deterministic id from reflection identifiers — no UUID, no time., EvolutionStore (+8 more)

### Community 26 - "Community 26"
Cohesion: 0.09
Nodes (13): LifecycleManager, brain/skill_creator/lifecycle_manager.py — Phase 7.9: LifecycleManager  Pipeline, Append-only, deterministic skill-lifecycle event log., LifecycleEvent, Immutable output of the Lifecycle stage (Phase 7.9, pipeline stage 08).      One, _entry(), tests/test_phase_7_step9.py — Milestone 7.9 (Lifecycle)  Pipeline stage 08 — app, TestBoundaries (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.14
Nodes (22): useChat(), useConnectionStatus(), useCrudResource(), useMemory(), useSocket(), useSocketEvent(), useArchive(), useEvents() (+14 more)

### Community 28 - "Community 28"
Cohesion: 0.09
Nodes (10): BlueprintBuilder, brain/skill_creator/blueprint_builder.py — Phase 7.2: BlueprintBuilder  Determin, Deterministic EvolutionRecommendationSet -> SkillBlueprintSet transformer., tests/test_phase_7_step2.py — Milestone 7.2 Verification (Blueprint Builder)  Ve, _rec(), _set(), TestBlueprintContent, TestBoundaries (+2 more)

### Community 29 - "Community 29"
Cohesion: 0.07
Nodes (20): BrainState, Any, Thread-safe, single source of runtime truth for Lumina V2.      Instantiate on, Return an immutable snapshot of the current state.          The snapshot is ta, Atomic mutation context manager.          Usage::              with brain_st, Convenience: update session fields atomically., Mark whether Gemini is actively generating a response turn., Switch active project atomically. (+12 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (26): ActionRouter, _clean_quest_title(), _extract_event_parts(), _extract_explicit_tag(), _extract_note_parts(), _fuzzy_match(), _infer_tag(), Action Router — Deterministic NL parser for Quests, Events, and Archive Notes. (+18 more)

### Community 31 - "Community 31"
Cohesion: 0.07
Nodes (25): ICapabilityMatcher, IDependencyResolver, IFailureRecovery, IRuntimePipeline, ISkillLoader, ISkillSandbox, ABC, brain/skill_runtime/interfaces.py — Phase 8.1: Registry Discovery contract  Beha (+17 more)

### Community 32 - "Community 32"
Cohesion: 0.07
Nodes (20): IPipelineMiddleware, Interface for a single pipeline middleware step.      Implementors:  PipelineM, Append a middleware to the end of the execution chain., Remove a previously-registered middleware from the chain., PipelineMiddleware, core/middleware.py — Lumina V2 Pipeline Middleware Base (Phase 1.5)  Base abst, Base class for RequestPipeline middleware.      Subclasses must implement `han, Human-readable identifier, defaults to the class name. (+12 more)

### Community 33 - "Community 33"
Cohesion: 0.07
Nodes (17): EvolutionRecommendation, EvolutionRecommendationSet, Immutable evolution recommendation (Phase 6.5).      Decides WHAT should evolve, Immutable set of evolution recommendations (Phase 6.5).      Deterministic snaps, Deterministic boolean risk flags for *skill_kind* (metadata only)., Derive descriptive skill blueprints from *recommendations*., Immutable collection of SkillBlueprint records (Phase 7.1)., Immutable request to derive blueprints from evolution recommendations     (Phase (+9 more)

### Community 34 - "Community 34"
Cohesion: 0.10
Nodes (11): BlueprintVerifier, brain/skill_creator/blueprint_verifier.py — Phase 7.3: BlueprintVerifier  Pipeli, Deterministic static verifier for a SkillBlueprint., _built(), tests/test_phase_7_step3.py — Milestone 7.3 (Blueprint Verification)  Pipeline s, TestBoundaries, TestDeterminismAndImmutability, TestFailures (+3 more)

### Community 35 - "Community 35"
Cohesion: 0.09
Nodes (21): InProcessEventBus, Any, brain/events.py — Lumina V2 InProcessEventBus  A lightweight, zero-dependency,, Holds one registered handler and its token., Return True if *topic* matches *pattern*.      Rules:     - Segments are spli, Concrete implementation of IEventBus.      Registered in the DI container as I, Publish *payload* to all subscribers whose pattern matches *topic*.          A, Register *callback* to receive events matching *topic*.         Returns a Subsc (+13 more)

### Community 36 - "Community 36"
Cohesion: 0.15
Nodes (11): CapabilityMatcher, brain/skill_runtime/capability_matcher.py — Phase 8.2: CapabilityMatcher  Semant, Deterministic, pure capability matching over discovered skills., CapabilityRequest, Immutable input to Capability Matching (Phase 8.2).      A semantic ask — "which, _FakeDiscovery, tests/test_phase_8_step2.py — Milestone 8.2 Verification (Capability Matching), IRegistryDiscovery stand-in. Records calls; never mutated by matcher. (+3 more)

### Community 37 - "Community 37"
Cohesion: 0.07
Nodes (14): _extract_keywords(), init_persona_engine(), PersonaEngine, Persona + Behavioral Initiative Engine for Lumina — v2 "Equal Partner"  Handle, Extract meaningful keywords from text, ignoring stopwords., Stateful persona engine. One instance per backend lifetime., Detect if user changed topics. Updates internal state., Compute adaptive tone modifiers. Returns dict with:         teasing, strictness (+6 more)

### Community 38 - "Community 38"
Cohesion: 0.11
Nodes (18): execute_local_browser(), Any, Return structured DOM state: clickables, inputs, headings, errors, focused_eleme, Return all visible interactive elements on the page., Switch the active tab by index., Execute a local browser action.      Args:         action:  one of the suppor, Return current tab state., Navigate the active tab to a URL. (+10 more)

### Community 39 - "Community 39"
Cohesion: 0.11
Nodes (15): BlueprintGenerator, brain/skill_creator/blueprint_generator.py — Phase 7.4: BlueprintGenerator  Pipe, Deterministic JSON: sorted keys, stable separators (no whitespace drift)., Deterministic package descriptor generator for a verified blueprint., IBlueprintGenerator, Blueprint generation contract (Phase 7.4, pipeline stage 03).      Consumes ONE, _built(), _fail() (+7 more)

### Community 40 - "Community 40"
Cohesion: 0.13
Nodes (16): IRollbackManager, Rollback contract (Phase 7.11, pipeline stage 10) — the final stage.      Consum, Path, brain/skill_creator/rollback_manager.py — Phase 7.11: RollbackManager  Pipeline, Remove *directory* (and empty parents up to root) if empty., Deterministic, idempotent installer-reversal. Owns no state., True if *candidate* is root or nested under it (lexical scope check)., RollbackManager (+8 more)

### Community 41 - "Community 41"
Cohesion: 0.06
Nodes (18): IWorkspaceManager, Path, Interface for project workspace management.      Implementors:  ProjectManager, Name of the currently-active project., Create a new project workspace.         Returns (success: bool, message: str)., Switch active project context.         Returns (success: bool, message: str)., Return names of all existing project workspaces., Return the filesystem path of the active project workspace. (+10 more)

### Community 42 - "Community 42"
Cohesion: 0.12
Nodes (33): _build_project(), _classify_error(), dev_agent(), _fix_files(), _get_model(), _has_error(), _install_dependencies(), _is_rate_limit() (+25 more)

### Community 43 - "Community 43"
Cohesion: 0.09
Nodes (11): BrainStateAdapter, EventBusAdapter, PipelineAdapter, Any, Forwards every call to a wrapped IBrainState implementation., Forwards every call to a wrapped IEventBus implementation., Forwards every call to a wrapped IPipeline implementation., Register thin pass-through adapters alongside the legacy/concrete         servi (+3 more)

### Community 44 - "Community 44"
Cohesion: 0.14
Nodes (14): Immutable runtime safety policy supplied to the Sandbox (Phase 8.4).      Descri, Immutable output of the Skill Sandbox (Phase 8.4).      A pure allow/deny verdic, SandboxDecision, SandboxPolicy, brain/skill_runtime/skill_sandbox.py — Phase 8.4: SkillSandbox  The first runtim, Deterministic, pure runtime safety gatekeeper., SkillSandbox, _perm() (+6 more)

### Community 45 - "Community 45"
Cohesion: 0.06
Nodes (26): Dev/Test Dependencies (requirements-dev.txt), printers(), Pytest configuration and shared fixtures for Lumina tests., Load settings.json for device configurations., Get printers from settings., Provide a temporary directory for file operations., Sample minimal STL file content for testing., sample_stl_content() (+18 more)

### Community 46 - "Community 46"
Cohesion: 0.13
Nodes (20): App(), getRoute(), ROUTES, PageHeader(), AppShell(), NavItem(), Sidebar(), STATUS_UI (+12 more)

### Community 47 - "Community 47"
Cohesion: 0.15
Nodes (21): SaveStatus(), SettingsError(), Button(), cloneDefaults(), DEFAULT_SETTINGS, useSettingsStatus(), filterPermissions(), PERMISSION_CATEGORIES (+13 more)

### Community 48 - "Community 48"
Cohesion: 0.14
Nodes (10): Discover the navigation skill id via deterministic capability ranking         (P, CapabilityResolver, Any, brain/skills/resolver.py — Phase 5.5 Step 4: Capability Ranking  CapabilityResol, Deterministic ranking over SkillMetadata., _md(), _MDRegistry, Register SkillMetadata directly (inputs/outputs/confirmation are empty     via f (+2 more)

### Community 49 - "Community 49"
Cohesion: 0.15
Nodes (13): BlueprintRegistry, brain/skill_creator/blueprint_registry.py — Phase 7.8: BlueprintRegistry  Pipeli, Append-only, deterministic catalog of installed skills., _built(), _installed(), _not_installed(), tests/test_phase_7_step8.py — Milestone 7.8 (Blueprint Registry)  Pipeline stage, TestAppendOnly (+5 more)

### Community 50 - "Community 50"
Cohesion: 0.09
Nodes (24): IBlueprintApprover, IBlueprintInstaller, IBlueprintRegistry, IBlueprintTester, IBlueprintVerifier, ILifecycleManager, IMarketplacePublisher, ISkillCreator (+16 more)

### Community 51 - "Community 51"
Cohesion: 0.13
Nodes (12): IRegistryDiscovery, Read-only discovery over the installed-skill registry (Phase 8.1)., Return the registered skills matching ``query``.          An empty query lists e, Any, brain/skill_runtime/registry_discovery.py — Phase 8.1: RegistryDiscovery  The fi, Deterministic, read-only discovery over the installed-skill registry., RegistryDiscovery, Phase 8.1: Registry Discovery — the first runtime consumer of the frozen (+4 more)

### Community 52 - "Community 52"
Cohesion: 0.11
Nodes (14): ContextInjector, Any, brain/skill_runtime/context_injector.py — Phase 8.7: ContextInjector  Prepares e, Deterministic, pure builder of an immutable ExecutionContext., IContextInjector, Context injection (Phase 8.7) — prepares everything a skill needs to run.      G, Build an immutable ExecutionContext for the loaded skill., ContextInjectionResult (+6 more)

### Community 53 - "Community 53"
Cohesion: 0.14
Nodes (14): ISkillExecutor, Skill executor (Phase 8.6) — runs a loaded skill exactly once.      Given a Load, Run the loaded skill once; return an immutable ExecutionResult., brain/skill_runtime/skill_executor.py — Phase 8.6: SkillExecutor  Runs a loaded, Runs one loaded skill; converts every failure into ExecutionResult., SkillExecutor, Phase 8.6: Skill Executor — runs a LoadedSkill exactly once via its         can, _BoomSkill (+6 more)

### Community 54 - "Community 54"
Cohesion: 0.15
Nodes (21): EmptyState(), ErrorToast(), DateTimeField(), FieldLabel(), SelectField(), TextArea(), TextField(), FilterTabs() (+13 more)

### Community 55 - "Community 55"
Cohesion: 0.10
Nodes (15): _new_id(), _prompt_line(), BaseModel, brain/workspace/models.py — Phase 5.6.1: Workspace Memory value objects  Frozen,, Prepared, read-only workspace recall carried on BrainContext (Phase 5.9.7)., Reduce a RetrievalHit to a single prompt-safe line, deterministically.      Pref, Deterministically project a WorkspaceRecallContext into prompt lines., Opaque unique identifier for a workspace record. (+7 more)

### Community 56 - "Community 56"
Cohesion: 0.09
Nodes (16): Produce evolution recommendations from the two analysis inputs., Aggregate stored observations into a StrategyAnalysis. Read-only., Measure execution quality from *strategy_analysis*. Read-only., ConsolidationProposalSet, PerformanceAnalysis, BaseModel, brain/evolution/models.py — Phase 6.1: Evolution observation value object  Froze, Immutable set of consolidation proposals (Phase 6.4).      Deterministic snapsho (+8 more)

### Community 57 - "Community 57"
Cohesion: 0.09
Nodes (19): DashboardServer, _decrypt_cbc(), _derive_key(), _ensure_network_access(), get_dashboard_server(), _local_ip(), _make_uploads_dir(), Any (+11 more)

### Community 58 - "Community 58"
Cohesion: 0.08
Nodes (29): get_persona_engine(), Compute per-turn memory injection budget.         Returns dict with max items p, _build_action_llm_prompt(), _build_alarm_dismiss_llm_prompt(), _build_followup_llm_prompt(), create_archive_note(), create_event(), delete_archive_note() (+21 more)

### Community 59 - "Community 59"
Cohesion: 0.12
Nodes (7): _bp(), _built(), tests/test_phase_7_step2_5.py — Milestone 7.2.5 Verification (Blueprint Schema H, TestBuilderPopulation, TestImmutability, TestRestrictedVocabulary, TestSchemaDefaults

### Community 60 - "Community 60"
Cohesion: 0.17
Nodes (10): ConsolidationProposal, Immutable proposal to consolidate memory records (Phase 6.4).      A PROPOSAL on, brain/evolution/recommender.py — Phase 6.5: RecommendationEngine (Self Evolution, Deterministic evolution-recommendation producer. Owns no state., RecommendationEngine, _consol(), _perf(), tests/test_phase_6_step5.py — Milestone 6.5 Verification (Self Evolution)  Verif (+2 more)

### Community 61 - "Community 61"
Cohesion: 0.14
Nodes (11): MarketplacePublisher, brain/skill_creator/marketplace_publisher.py — Phase 7.10: MarketplacePublisher, Deterministic marketplace-manifest constructor. Owns no state., _built(), _entry(), tests/test_phase_7_step10.py — Milestone 7.10 (Marketplace)  Pipeline stage 09 —, TestBoundaries, TestContent (+3 more)

### Community 62 - "Community 62"
Cohesion: 0.12
Nodes (14): IRuntimeValidator, Runtime Validation checker (Phase 8.13) — read-only integrity assertion.      Co, Return an immutable ValidationReport for *result*., _index(), brain/skill_runtime/runtime_validation.py — Phase 8.13: RuntimeValidator  Read-o, Deterministic, read-only pipeline-result integrity checker. Repairs nothing., RuntimeValidator, Phase 8.13: Runtime Validation — read-only integrity checker over a         Run (+6 more)

### Community 63 - "Community 63"
Cohesion: 0.07
Nodes (15): IMemoryManager, Persist a new memory. Returns the assigned database row id., Promote a memory record (e.g. pending → active)., Demote a memory record (e.g. active → dormant)., Bump access count and priority for a recently-accessed record., Retrieve memories, optionally filtered by type., Return identity-anchor memories that should always be injected., Return the most-recent session summary for continuity injection. (+7 more)

### Community 64 - "Community 64"
Cohesion: 0.17
Nodes (11): BlueprintApprover, brain/skill_creator/blueprint_approver.py — Phase 7.6: BlueprintApprover  Pipeli, Deterministic human-approval gate over a TestResult., _built(), _failed_test(), _passing_test(), tests/test_phase_7_step6.py — Milestone 7.6 (Blueprint Approval)  Pipeline stage, TestBoundaries (+3 more)

### Community 65 - "Community 65"
Cohesion: 0.19
Nodes (12): BlueprintInstaller, brain/skill_creator/blueprint_installer.py — Phase 7.7: BlueprintInstaller  Pipe, Deterministic, idempotent installer of an approved generated package., _approval(), _built(), _gen(), tests/test_phase_7_step7.py — Milestone 7.7 (Blueprint Installation)  Pipeline, TestBoundaries (+4 more)

### Community 66 - "Community 66"
Cohesion: 0.13
Nodes (11): ExecutionObserver, brain/skill_runtime/execution_observer.py — Phase 8.8: ExecutionObserver  Purely, Deterministic, read-only observer of execution outcomes., IExecutionObserver, Execution observer (Phase 8.8) — purely observational.      Converts an immutabl, Return an immutable ExecutionObservation for *result*., ExecutionResult, Immutable result of the Skill Executor (Phase 8.6).      Records the outcome of (+3 more)

### Community 67 - "Community 67"
Cohesion: 0.22
Nodes (26): _build(), _clean_code(), code_helper(), _detect_intent(), _edit_action(), _explain_action(), _fix_code(), _get_api_key() (+18 more)

### Community 68 - "Community 68"
Cohesion: 0.14
Nodes (26): _action_focus(), _action_next(), _action_open(), _action_open_library(), _action_open_liked(), _action_pause(), _action_play(), _action_play_query() (+18 more)

### Community 69 - "Community 69"
Cohesion: 0.13
Nodes (10): MemoryConsolidator, Any, brain/evolution/consolidator.py — Phase 6.4: MemoryConsolidator  Read-only memor, Deterministic, read-only duplicate-consolidation proposer., Stable content signature from title + body-like fields (no id)., tests/test_phase_6_step4.py — Milestone 6.4 Verification (Memory Consolidation), Duck-typed memory record: id + title/body., _Rec (+2 more)

### Community 70 - "Community 70"
Cohesion: 0.18
Nodes (8): DependencyResolver, brain/skill_runtime/dependency_resolver.py — Phase 8.3: DependencyResolver  The, Deterministic, pure dependency gate over matched skills., _matches(), tests/test_phase_8_step3.py — Milestone 8.3 Verification (Dependency Resolution), _skill(), TestBoundaries, TestResolve

### Community 71 - "Community 71"
Cohesion: 0.09
Nodes (12): Append a task record., Return tasks in insertion order., Return an immutable WorkspaceSnapshot of the current state., Immutable view of the current state (insertion order preserved)., A project task / TODO item (workspace-scoped, distinct from quests)., Immutable read-only view of a workspace's structured memory.      This is what C, WorkspaceSnapshot, WorkspaceTask (+4 more)

### Community 72 - "Community 72"
Cohesion: 0.23
Nodes (7): _fail(), _ok(), _plan(), tests/test_phase_5_7_step2.py — Phase 5.7.2: ReflectionEngine  Pure deterministi, _req(), TestComputation, TestDeterminismAndPurity

### Community 73 - "Community 73"
Cohesion: 0.08
Nodes (15): IKnowledgeManager, IModelGateway, ABC, core/interfaces.py — Lumina V2 Contract Layer  Abstract base class interfaces, Interface for the hybrid semantic + lexical retrieval engine.      Implementor, Hybrid search (vector + keyword).         Returns at most top_k ranked excerpt, Synchronous fallback for search_memory.         Used when an asyncio executor i, Persist a conversation transcript line. Returns row id or None. (+7 more)

### Community 74 - "Community 74"
Cohesion: 0.08
Nodes (12): IWorkspaceMemory, Structured, in-memory project-memory contract., Set (replace) the project info record., Return the current project info, or None if unset., Append a decision record., Return decisions in insertion order., Append a note record., Return notes in insertion order. (+4 more)

### Community 75 - "Community 75"
Cohesion: 0.11
Nodes (7): PromptWorkspaceContext, Prompt-safe projection of WorkspaceRecallContext (Phase 5.9.8).      ==== ARCHIT, TestBoundaries, tests/test_phase_5_9_step9.py — Milestone 5.9.9 (Workspace Context Injection)  V, TestBoundaries, TestFormatter, TestPromptInjection

### Community 76 - "Community 76"
Cohesion: 0.16
Nodes (4): Step 1: RulePlanner output must reference the truth-aligned catalog.      Every, Step 2: LLMPlanner async planning path (fixes D4/D1).      plan_async() must dri, TestStep1_RulePlannerContract, TestStep2_LLMPlannerAsync

### Community 77 - "Community 77"
Cohesion: 0.14
Nodes (9): _built(), _gen(), _not_generated(), tests/test_phase_7_step5.py — Milestone 7.5 (Blueprint Testing)  Pipeline stage, TestBoundaries, TestCategories, TestDeterminismImmutability, TestGate (+1 more)

### Community 78 - "Community 78"
Cohesion: 0.19
Nodes (8): Path, brain/skill_runtime/skill_loader.py — Phase 8.5: SkillLoader  Turns an approved, Loads an approved skill package into a validated instance. No execution., SkillLoader, _decision(), tests/test_phase_8_step5.py — Milestone 8.5 Verification (Skill Loader)  Turns a, TestLoader, _write_skill()

### Community 79 - "Community 79"
Cohesion: 0.11
Nodes (10): True if this executor can run *spec*., Derive metadata from a registered SkillSpec.          *source* records where the, BaseModel, brain/skills/models.py — Phase 5.2 skill value objects  Pure pydantic data model, Metadata describing one skill. Descriptive only — no implementation., SkillSpec, Register a SkillSpec. Duplicate ids raise — one owner per id.          Phase 5.5, Discover skills by free-text query and/or tags.          - query: case-insensiti (+2 more)

### Community 80 - "Community 80"
Cohesion: 0.11
Nodes (12): brain/skills/metadata.py — Phase 5.5 Step 1: Skill Metadata foundation  A struct, Immutable structured metadata for one skill.      Frozen dataclass; sequence fie, SkillMetadata, Return derived metadata for every registered skill (Phase 5.5)., Capability discovery over SkillMetadata (Phase 5.5 Step 2).          Read-only,, Rank all registered skills against the signals and return the single         bes, Deterministic additive score of *md* against the requested signals.         Each, Return *candidates* ordered by score (desc), ties broken by the         original (+4 more)

### Community 81 - "Community 81"
Cohesion: 0.11
Nodes (12): ArchitectureRecall, NotesRecall, Any, brain/workspace/recall.py — Phase 5.9.3–5.9.6: Workspace recall consumers  Thin,, Thin, read-only note recall over IWorkspaceRetriever., Delegate to the retriever, narrowed to note records., Thin, read-only task recall over IWorkspaceRetriever., Delegate to the retriever, narrowed to task records. (+4 more)

### Community 82 - "Community 82"
Cohesion: 0.09
Nodes (13): Any, core/service_accessor.py — Lumina V2 Service Accessor Bridge (Phase 3)  Provid, True if a memory store is available from either source., True if a project manager is available from either source., True if a knowledge manager is available from either source., Return the current project name, or None., Safe bridge for resolving IMemoryManager, IWorkspaceManager, and     IKnowledge, Resolve IMemoryManager from DI container, falling back to         SessionManage (+5 more)

### Community 83 - "Community 83"
Cohesion: 0.14
Nodes (19): BrainSnapshot, ConversationMeta, ExecutionContext, _MutableDraft, PlannerContext, BaseModel, brain/state.py — Lumina V2 BrainState  Single thread-safe source of runtime tr, Conversation-level metadata for the current session. (+11 more)

### Community 84 - "Community 84"
Cohesion: 0.09
Nodes (12): Any, Detect intent and assumption signals.         Returns list of detected memory d, Return stale pending memories that should be revisited., Subscribe to a topic pattern (supports wildcards).         Returns a Subscripti, Remove a subscription by its token., Synchronous subscribe. Returns a SubscriptionToken., Synchronous unsubscribe by token., Return a diagnostic snapshot of the subscription table. (+4 more)

### Community 85 - "Community 85"
Cohesion: 0.11
Nodes (12): core/metadata.py — Lumina V2 Service Metadata (Phase 1.8)  Descriptive metadat, Immutable descriptor for one registered infrastructure service.      name, In-memory registry of ServiceMetadata records.      Purely additive and indepe, Store a metadata record (overwrites any existing record for its key)., Return the metadata record for *key*, or None if absent., Return all metadata records in registration order of insertion., ServiceMetadata, ServiceMetadataRegistry (+4 more)

### Community 86 - "Community 86"
Cohesion: 0.09
Nodes (6): MemoryStore, Passive memory storage for Lumina.          Memory Types:     - fact: Factual, Search memories by content.                  Args:             query: Search, Demote a memory (e.g., active → dormant). Returns True if updated., Mark a memory as used — bumps priority and last_used_at., Get memory store statistics.

### Community 87 - "Community 87"
Cohesion: 0.13
Nodes (7): _bp(), _built(), tests/test_phase_7_step2_6.py — Milestone 7.2.6 (SkillBlueprint Schema Freeze), TestDeterminism, TestNoBehavior, TestReservedContracts, TestSubModelsFrozen

### Community 88 - "Community 88"
Cohesion: 0.24
Nodes (21): copy_file(), create_file(), create_folder(), delete_file(), file_controller(), find_files(), _format_size(), _get_desktop() (+13 more)

### Community 89 - "Community 89"
Cohesion: 0.14
Nodes (7): brain/workspace/sync.py — Phase 5.6.6: WorkspaceSync coordinator  Bridges Projec, Follows ProjectManager; keeps WorkspaceMemoryManager in step., WorkspaceSync, _FakePM, _FakeWSM, WorkspaceMemoryManager stand-in recording switch/save/current calls., TestActivationSync

### Community 90 - "Community 90"
Cohesion: 0.10
Nodes (14): AgentContext, AgentResult, BaseAgent, ABC, Base agent interface for Lumina.  Inspired by OpenJarvis agent abstractions. P, Context passed to an agent when executing a task., Standard result returned by an agent., Abstract base class for Lumina agents. (+6 more)

### Community 91 - "Community 91"
Cohesion: 0.16
Nodes (9): IEventBus, IPipeline, Interface for the async publish/subscribe Event Bus.      NOTE: The Event Bus, Publish an event payload to a topic string., Synchronous publish. Delivers to sync handlers in the caller's thread., Interface for a generic, ordered middleware execution pipeline.      Implement, Remove all registered middleware., ArchitectureValidator (+1 more)

### Community 93 - "Community 93"
Cohesion: 0.10
Nodes (21): AES-256-CBC Encryption (CryptoJS), /api/command endpoint, /api/upload endpoint, /api/wake endpoint, AudioWorklet audio capture, JARVIS Dashboard (app.html), JARVIS Login (login.html), /login endpoint (+13 more)

### Community 94 - "Community 94"
Cohesion: 0.20
Nodes (8): PerformanceAnalyzer, brain/evolution/analyzer.py — Phase 6.3: PerformanceAnalyzer  Deterministic perf, Deterministic performance metrics over a StrategyAnalysis., _analysis(), tests/test_phase_6_step3.py — Milestone 6.3 Verification (Performance Analysis), _stat(), TestAnalyzer, TestBoundaries

### Community 95 - "Community 95"
Cohesion: 0.20
Nodes (8): brain/evolution/evaluator.py — Phase 6.2: StrategyEvaluator  Deterministic analy, Deterministic per-strategy analysis over the observation store., StrategyEvaluator, _obs(), tests/test_phase_6_step2.py — Milestone 6.2 Verification (Strategy Improvement), _store(), TestBoundaries, TestEvaluator

### Community 96 - "Community 96"
Cohesion: 0.18
Nodes (9): FailureRecovery, brain/skill_runtime/failure_recovery.py — Phase 8.12: FailureRecovery  Descripti, Deterministic, descriptive recovery advisor. Acts on nothing., tests/test_phase_8_step12.py — Milestone 8.12 (Failure Recovery)  Verifies the d, _result(), TestBoundaries, TestCompleted, TestFailureMapping (+1 more)

### Community 97 - "Community 97"
Cohesion: 0.15
Nodes (12): Any, T, Generic registry base class with class-specific entry isolation., Decorator that registers *entry* under *key*., Imperatively register a *value* under *key*., Retrieve the entry for *key*, raising ``KeyError`` if missing., Look up *key* and instantiate it with the given arguments., Return all ``(key, entry)`` pairs as a tuple. (+4 more)

### Community 98 - "Community 98"
Cohesion: 0.15
Nodes (16): IEvolutionObserver, IMemoryConsolidator, IPerformanceAnalyzer, IRecommendationEngine, IStrategyEvaluator, ABC, Any, brain/evolution/interfaces.py — Phase 6.1: Evolution observation contracts  Beha (+8 more)

### Community 99 - "Community 99"
Cohesion: 0.11
Nodes (11): ISkillRegistry, ABC, brain/skills/interfaces.py — Phase 5.5 Step 1: skill-layer contract  ISkillRegis, Metadata storage and discovery contract for the skill layer., Register a SkillSpec with an optional origin source. Duplicate ids raise., Return the SkillSpec for *skill_id*, or None., Discover skills by free-text query and/or tags., Return every registered SkillSpec. (+3 more)

### Community 100 - "Community 100"
Cohesion: 0.27
Nodes (8): DecisionRecall, Thin, read-only decision recall over IWorkspaceRetriever., _canned(), tests/test_phase_5_9_step3.py — Milestone 5.9.3 Verification (DecisionRecall)  V, IWorkspaceRetriever stand-in recording calls; returns a canned result., _SpyRetriever, TestDelegation, TestReadOnly

### Community 101 - "Community 101"
Cohesion: 0.15
Nodes (13): ExecutionContext, ExecutionContextFactory, _new_id(), Any, Derive a child context for sub-work spawned by this context.          The chil, Constructs root ExecutionContext instances.      This is the only supported wa, Create a new root ExecutionContext with a fresh correlation_id., Convenience constructor that seeds a root context from a         BrainState sna (+5 more)

### Community 102 - "Community 102"
Cohesion: 0.13
Nodes (17): _cdp_reachable(), _detect_brave_exe(), _ensure_lumina_dirs(), _launch_brave(), _lumina_browser_running_without_debug(), _needs_confirmation(), Phase T2: Local Browser Control — Lumina's dedicated Brave browser.  Lumina ow, Determine if a non-blocked action needs user confirmation.     Returns (needs_c (+9 more)

### Community 103 - "Community 103"
Cohesion: 0.12
Nodes (14): Import an action function and register it, logging any import failures., _try_register(), Lumina core — registries, base classes, shared types, and DI container., ActionRegistry, AgentRegistry, Decorator-based registry for runtime discovery of pluggable components.  Adapt, Registry for action functions (imported from actions/ modules)., Registry for agent implementations (CadAgent, KasaAgent, etc.). (+6 more)

### Community 104 - "Community 104"
Cohesion: 0.14
Nodes (8): ProjectManager, Returns the last 'limit' chat messages from history., Creates a new project directory with subfolders., Switches the active project context., Returns a list of available projects., Appends a chat message to the current project's history., Copies a generated CAD file to the project's 'cad' folder., Gathers context about the current project for the AI.         Lists all files a

### Community 105 - "Community 105"
Cohesion: 0.15
Nodes (10): Any, T, Register *factory* as the provider for *interface*.         The factory is call, Directly register a pre-built *instance* for *interface*.         Semantically, Force-replace an existing binding with a pre-built instance.         Intended f, Return the implementation bound to *interface*.          - SINGLETON: creates, Return True if *interface* has a binding in this container., Internal record stored for each registered interface. (+2 more)

### Community 106 - "Community 106"
Cohesion: 0.13
Nodes (12): _flush_transcript_buffer_if_stale(), _index_transcript_bg(), Buffers raw transcript fragments; flushes to MEMORY2 only when stable., Buffer a raw transcript fragment. Does NOT store to DB., Return flushed text if flush conditions are met, else None., Force-flush buffer (e.g. on real user turn). Returns text or None., Flush any buffers older than silence_flush_s. Returns [(role, text)]., Store+index a flushed transcript chunk via MEMORY2, offloaded to thread (FIX C). (+4 more)

### Community 107 - "Community 107"
Cohesion: 0.14
Nodes (4): tests/test_phase_5_5_step2.py — Phase 5.5 Step 2: Capability Discovery  Proves r, _spec(), TestRegistrationUnchanged, TestSearchBySpecDerived

### Community 108 - "Community 108"
Cohesion: 0.17
Nodes (10): DummyAudioLoop, DummyMemoryStore, DummyProjectManager, _fail(), make_clean_context(), _ok(), brain/test_phase_3.py — Phase 3 Standalone Architectural Verification Tests (Iso, Helper to return an isolated sandbox environment. (+2 more)

### Community 109 - "Community 109"
Cohesion: 0.14
Nodes (17): kill_browser_tools(), local_browser_open(), memory_confirm_endpoint(), memory_deny_endpoint(), memory_search(), Emergency kill switch — instantly disable all browser tools for session., Hybrid memory search. Body: {"query": "...", "top_k": 8}, Promote a pending memory to active. Body: {"id": <int>} (+9 more)

### Community 110 - "Community 110"
Cohesion: 0.15
Nodes (10): _fail(), _ok(), test_phase_2_1.py — Lumina V2 Phase 2.1 Verification Tests  Tests:   1. Boots, run_tests(), _section(), IBrainState, Interface for the central runtime state manager.      Implementors:  BrainStat, Return an immutable frozen BrainSnapshot representing the current state. (+2 more)

### Community 111 - "Community 111"
Cohesion: 0.29
Nodes (3): Duck-typed ProjectManager: only get_current_project_path() is used., _StubProjectManager, TestSync

### Community 112 - "Community 112"
Cohesion: 0.28
Nodes (5): _canned(), tests/test_phase_5_9_step456.py — Milestones 5.9.4–5.9.6 Verification  NotesReca, IWorkspaceRetriever stand-in recording calls; returns a canned result., _SpyRetriever, TestRecallConsumers

### Community 113 - "Community 113"
Cohesion: 0.19
Nodes (6): FaceAuthenticator, :param reference_image_path: Path to the user's reference photo.         :param, Download the MediaPipe Face Landmarker model if not present., Initialize the MediaPipe Face Landmarker., Extract normalized face landmarks from an RGB image.         Returns a flattene, Compare two landmark vectors using cosine similarity.         Returns True if s

### Community 114 - "Community 114"
Cohesion: 0.19
Nodes (13): _fail(), _ok(), test_phase_2_5.py — Lumina V2 Phase 2.5 Verification Tests  Tests:   1. Boots, run_tests(), _section(), _fail(), _ok(), test_phase_2_8.py — Lumina V2 Phase 2.8 Verification Tests  Tests:   1. Boots (+5 more)

### Community 115 - "Community 115"
Cohesion: 0.31
Nodes (11): useSystemInfo(), fmt(), getDeviceCounts(), getDisplayInfo(), getEnvironmentInfo(), getRuntimeInfo(), nav(), parseUserAgent() (+3 more)

### Community 116 - "Community 116"
Cohesion: 0.23
Nodes (13): _open_url(), actions/send_message.py — Lumina messaging action  Opens WhatsApp Web / Telegr, Open Telegram Web and attempt to navigate to a contact.      Telegram does not, Open Instagram DMs.      Instagram does not support pre-filled DM deep-links f, Lumina messaging action. Opens WhatsApp/Telegram/Instagram and sends a message., Open a URL in the default browser. Returns True on success., Type text using clipboard for reliability., Open WhatsApp Web with a pre-filled message link.      WhatsApp supports wa.me (+5 more)

### Community 117 - "Community 117"
Cohesion: 0.14
Nodes (7): Return note records matching *query*., Return task records matching *query*., Return architecture records matching *query*., Return records matching *query* and optional filters, read-only.          ``reco, Immutable, serializable result of a retrieval query (Phase 5.9.1).      ``hits``, WorkspaceRetrievalResult, Delegate to the retriever, narrowed to decision records.

### Community 118 - "Community 118"
Cohesion: 0.19
Nodes (9): ExecutionContextAdapter, Forwards every call to a wrapped IExecutionContext implementation.      child(, IExecutionContext, Interface for an immutable execution-context value object.      Implementors:, Resolve a fresh ExecutionContextAdapter (transient — one per call).          N, check(), core/test_phase_1_6.py — Phase 1.6 verification tests (Infrastructure Adapters), run() (+1 more)

### Community 119 - "Community 119"
Cohesion: 0.20
Nodes (7): HealthReporter, Any, Health record for a single infrastructure service., Produces read-only health reports for infrastructure services.      Each probe, Return a health record for each known infrastructure service., True if every probed service reports STATUS_OK., ServiceHealth

### Community 120 - "Community 120"
Cohesion: 0.26
Nodes (5): _FakeFacade, _FakeFacadeBoom, _FakeLoop, tests/test_phase_5_8_step2.py — Milestone 5.8.2 Verification (Workspace Activati, TestActivationTrigger

### Community 121 - "Community 121"
Cohesion: 0.26
Nodes (13): main(), print_header(), Test 3: Test relevant memory retrieval with identity query, Test 4: Simulate message assembly and verify format, Test 5: Verify identity memories are ALWAYS included regardless of relevance, Run all Phase C validation tests, Test 1: Ensure memory database exists, Test 2: Ensure identity memories are present and retrievable (+5 more)

### Community 122 - "Community 122"
Cohesion: 0.19
Nodes (5): ExecutionObservation, Immutable observational record of one execution outcome (Phase 8.8).      Descri, tests/test_phase_8_step8.py — Milestone 8.8 Verification (Execution Observer)  P, TestBoundaries, TestModel

### Community 123 - "Community 123"
Cohesion: 0.19
Nodes (9): _fail(), _ok(), test_phase_2_4.py — Lumina V2 Phase 2.4 Verification Tests  Tests:   1. Boots, run_tests(), _section(), PipelineContext, Per-execution data passed through a RequestPipeline.      execution_context  E, Mark this execution as cancelled. Middleware may check is_cancelled. (+1 more)

### Community 124 - "Community 124"
Cohesion: 0.21
Nodes (11): IArchitectureRecall, IDecisionRecall, INotesRecall, ITaskRecall, ABC, brain/workspace/interfaces.py — Phase 5.6.2: WorkspaceMemory contract  IWorkspac, Read-only recall of decision records (Phase 5.9.3).      First consumer of the f, Return decision records matching *query*. (+3 more)

### Community 125 - "Community 125"
Cohesion: 0.15
Nodes (7): LocalBrowserController, Return info about all open tabs., Manages a CDP connection to Lumina's dedicated Brave browser instance., Cleanly disconnect (does NOT close Brave)., Click an element by CSS selector., Open a new browser tab, optionally navigating to a URL., Return comprehensive state of the active tab.

### Community 126 - "Community 126"
Cohesion: 0.17
Nodes (12): computer_settings(), _detect_action(), press_key(), Close a named application by process name. Safer than blind Alt+F4., Use Gemini to detect the intended action from a natural language description., Lumina computer settings & UI control action.      parameters:         action, refresh_page(), reload_page_n() (+4 more)

### Community 127 - "Community 127"
Cohesion: 0.17
Nodes (6): IEvolutionStore, Append-only store of EvolutionObservation records. No update/delete., Append one observation. Never overwrites an existing record., Return the observation with *observation_id*, or None., Return all observations in insertion order (copy)., Return the number of stored observations.

### Community 128 - "Community 128"
Cohesion: 0.20
Nodes (4): handle_create_project(), handle_switch_project(), _maybe_activate_workspace(), Phase 5.8.2 — flag-gated Workspace Activation trigger.      After ProjectManag

### Community 129 - "Community 129"
Cohesion: 0.17
Nodes (4): # NOTE: run_web_agent REMOVED — Web Agent is disabled in this build., # NOTE: 'continue' removed here to allow processing transcription/tools in same, Lumina Passive Memory Store  This module provides PASSIVE memory storage for L, Phase B.1 Verification Tests  Tests: 1. Environment check (must be in lumina

### Community 130 - "Community 130"
Cohesion: 0.17
Nodes (3): tests/test_phase_5_5.py — Phase 5.5 Step 1: Skill Metadata foundation  Proves:, TestRegistryMetadata, TestSkillSpecUntouched

### Community 131 - "Community 131"
Cohesion: 0.23
Nodes (11): main(), Phase E3 - Continuity Memory + Voice Approval Test  Tests: 1. Session summary, Test that session summaries are injected into memory context (Phase E3)., Test that voice approval only works within 30 seconds of suggestion (Phase E3)., Test that session summaries are rate-limited (max 1 per 30 minutes) (Phase E3)., Run all Phase E3 tests, Test voice approval for memory suggestions (Phase E3)., test_session_summary_injection() (+3 more)

### Community 132 - "Community 132"
Cohesion: 0.24
Nodes (10): local_browser_status(), Generate a Lumina reply for a WhatsApp message received in the UI., Check if CDP is reachable and return current tab state., whatsapp_reply(), _cdp_reachable(), generate_lumina_reply(), poll_unread_messages(), Quick check if Lumina's dedicated CDP endpoint is responding on port CDP_PORT. (+2 more)

### Community 133 - "Community 133"
Cohesion: 0.24
Nodes (4): _occupy(), tests/test_port_recovery.py — Milestone 4.1 regression tests  Verifies the grace, Bind and listen on (HOST, port); caller must close the returned socket.      No, TestPortRecovery

### Community 134 - "Community 134"
Cohesion: 0.20
Nodes (3): Register MemoryEngine (IKnowledgeManager) as a LAZY singleton.          Constr, Build and seal a RequestPipeline via PipelineBuilder.          No middleware i, Construct and register all services owned by this bootstrapper.

### Community 135 - "Community 135"
Cohesion: 0.20
Nodes (5): Retrieve memories filtered by state (active, pending, dormant)., Get active memories ordered by priority for prompt injection., Get pending assumptions for cautious injection or revisit., Get pending memories older than threshold for natural revisit., Convert a full row (with lifecycle fields) to dict.

### Community 136 - "Community 136"
Cohesion: 0.24
Nodes (3): tests/test_phase_7_step1.py — Milestone 7.1 Verification (Skill Creator Foundati, TestBoundaries, TestInterface

### Community 137 - "Community 137"
Cohesion: 0.39
Nodes (8): _find_windows_executable(), _focus_or_open(), _is_running(), open_app(), _open_linux(), _open_mac(), _open_windows(), Lumina application launcher action.      parameters:         app     : App na

### Community 138 - "Community 138"
Cohesion: 0.42
Nodes (6): FeatureCard(), FEATURE_CATEGORIES, FEATURE_COLOR_MAP, FEATURES, filterFeatures(), SkillsPage()

### Community 139 - "Community 139"
Cohesion: 0.25
Nodes (5): Add a new memory entry.                  Args:             memory_type: Type, Retrieve memories, optionally filtered by type.                  Args:, Get a formatted memory context string for conversation enhancement., MemoryState, MemoryType

### Community 140 - "Community 140"
Cohesion: 0.25
Nodes (5): Test that landmarks have correct format when detected., Test face landmark extraction., Create an authenticated FaceAuthenticator., Test extraction from blank image (should return None)., TestLandmarkExtraction

### Community 141 - "Community 141"
Cohesion: 0.25
Nodes (5): Test face landmark comparison., Test comparing identical landmarks., Test comparing completely different landmarks., Test comparison with different thresholds., TestLandmarkComparison

### Community 142 - "Community 142"
Cohesion: 0.25
Nodes (5): Test required dependencies., Test MediaPipe is installed., Test OpenCV is installed., Test NumPy is installed., TestDependencies

### Community 143 - "Community 143"
Cohesion: 0.25
Nodes (5): Test MediaPipe Face Landmarker model., Test that model path is defined., Test that model URL is defined., Test model download/verification., TestMediaPipeModel

### Community 144 - "Community 144"
Cohesion: 0.39
Nodes (3): _ctx(), tests/test_phase_5_5_step4.py — Phase 5.5 Step 4: Capability Ranking  Capability, TestPlannerIntegration

### Community 145 - "Community 145"
Cohesion: 0.29
Nodes (4): Tests for Face Authentication., Test camera access functions., Test that camera-related methods exist., TestCameraAccess

### Community 146 - "Community 146"
Cohesion: 0.33
Nodes (3): LoadedSkill, Immutable result of the Skill Loader (Phase 8.5).      Turns an approved skill d, TestModel

### Community 147 - "Community 147"
Cohesion: 0.33
Nodes (6): Return the latest screenshot frame from the browser frame cache., vision_latest(), get_local_browser_controller(), check(), main(), Quick sanity test for local_browser_control — CDP + Brave.

### Community 148 - "Community 148"
Cohesion: 0.38
Nodes (6): main(), Phase E2 - Memory Suggestion System Test  Tests the human-like memory system w, Verify that memory is NOT auto-saved without user approval., Test the complete memory suggestion flow:     1. Send a message that should tri, test_memory_suggestion_flow(), test_no_auto_save()

### Community 149 - "Community 149"
Cohesion: 0.52
Nodes (3): ChatMessage(), MessageBubble(), TypingIndicator()

### Community 150 - "Community 150"
Cohesion: 0.53
Nodes (5): _fail(), _ok(), test_phase_2_2.py — Lumina V2 Phase 2.2 Verification Tests  Tests:   1. Boots, run_tests(), _section()

### Community 151 - "Community 151"
Cohesion: 0.53
Nodes (5): _fail(), _ok(), test_phase_2_3.py — Lumina V2 Phase 2.3 Verification Tests  Tests:   1. Boots, run_tests(), _section()

### Community 152 - "Community 152"
Cohesion: 0.53
Nodes (5): _fail(), _ok(), test_phase_2_6.py — Lumina V2 Phase 2.6 Verification Tests  Tests:   1. Boots, run_tests(), _section()

### Community 153 - "Community 153"
Cohesion: 0.53
Nodes (5): _fail(), _ok(), test_phase_2_7.py — Lumina V2 Phase 2.7 Verification Tests  Tests:   1. Boots, run_tests(), _section()

### Community 154 - "Community 154"
Cohesion: 0.33
Nodes (3): Safe migration: add missing columns and fix CHECK constraint. Preserves all data, Initialize memory store.                  Args:             db_path: Path to, Initialize database schema if it doesn't exist.

### Community 155 - "Community 155"
Cohesion: 0.33
Nodes (4): Test reference image handling., Test default reference image path., Test loading reference image., TestReferenceImage

### Community 156 - "Community 156"
Cohesion: 0.33
Nodes (4): Test FaceAuthenticator initialization., Test FaceAuthenticator can be created., Test FaceAuthenticator with callbacks., TestAuthenticatorInit

### Community 157 - "Community 157"
Cohesion: 0.33
Nodes (4): Test AudioLoop class structure., Test AudioLoop class can be imported., Test AudioLoop has required methods., TestAudioLoopClass

### Community 158 - "Community 158"
Cohesion: 0.33
Nodes (4): Test Gemini Live Connect configuration., Test config is defined., Test config includes audio modality., TestLiveConnectConfig

### Community 159 - "Community 159"
Cohesion: 0.33
Nodes (4): _normalize_text(), Click the best matching element with strict scoring (>=85) and filtering., Fuzzy-match visible text/aria_label and click the best candidate., Normalize text for matching: lowercase, collapse whitespace, strip emoji/symbols

### Community 160 - "Community 160"
Cohesion: 0.40
Nodes (5): Example Domain page (example.com) loaded, Example Domain page (example.com) loaded (duplicate frame), Google 'About this page' unusual traffic check — search q=Playwright+Python+testing, Google 'About this page' unusual traffic check — search q=asyncio+Python, Example Domain page (example.com) loaded (later step)

### Community 161 - "Community 161"
Cohesion: 0.40
Nodes (5): Google 'About this page' unusual traffic CAPTCHA (query: Playwright+Python testing, 2026-02-08T14:49:37Z), Google 'About this page' unusual traffic CAPTCHA (query: asyncio Python, 2026-02-08T14:49:40Z), Example Domain page (example.com documentation domain, Learn more link), Example Domain page (duplicate state of example.com), Google 'About this page' unusual traffic CAPTCHA (query: Playwright+Python testing, 2026-02-08T15:08:57Z)

### Community 162 - "Community 162"
Cohesion: 0.40
Nodes (4): format_workspace_context(), Any, brain/planning/prompt_builder.py — Phase 5.9.10: workspace prompt formatting  De, Format PromptWorkspaceContext into a deterministic prompt section.      Empty/ab

### Community 163 - "Community 163"
Cohesion: 0.60
Nodes (4): check(), core/test_phase_1_7.py — Phase 1.7 verification tests (Service Resolution Helper, run(), section()

### Community 167 - "Community 167"
Cohesion: 0.50
Nodes (4): Example Domain page (browser step), Google unusual traffic check - Playwright Python testing query, Google unusual traffic check - asyncio Python query, Example Domain page (browser step, duplicate state)

### Community 168 - "Community 168"
Cohesion: 0.67
Nodes (4): Video feed empty state prompt (Nepali) with search box, Google 'unusual traffic' CAPTCHA block page for nepali chill songs query, Google 'unusual traffic' CAPTCHA block page for site:youtube.com query, YouTube 'Soft Nepali Lofi' video watch page loading (1:09:50)

### Community 171 - "Community 171"
Cohesion: 0.67
Nodes (3): main(), Run pytest with specified options., run_tests()

### Community 173 - "Community 173"
Cohesion: 0.67
Nodes (3): copy(), paste(), type_text()

## Knowledge Gaps
- **35 isolated node(s):** `VARIANTS`, `SIZES`, `DEFAULT_SETTINGS`, `STATUS_UI`, `TYPES` (+30 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **33 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Bootstrapper` connect `Infrastructure Adapters & App Host` to `BrainCore Orchestrator`, `Rule Planner & Skill Seeding`, `Planner Contracts & BrainContext`, `Skill Runtime Persistence`, `Dev Agent / Package Generator`, `Community 134`, `Memory Engine & Embeddings`, `Legacy Session Dispatch`, `Context Builder`, `Community 136`, `Runtime Pipeline Orchestrator`, `Workspace Memory Manager`, `Community 146`, `Capability Matching`, `Community 25`, `Community 26`, `Community 28`, `Community 29`, `Community 31`, `Community 32`, `Community 33`, `Community 34`, `Community 35`, `Community 36`, `Community 165`, `Community 166`, `Community 39`, `Community 40`, `Community 43`, `Community 44`, `Community 49`, `Community 50`, `Community 51`, `Community 52`, `Community 53`, `Community 56`, `Community 60`, `Community 61`, `Community 62`, `Community 64`, `Community 65`, `Community 66`, `Community 69`, `Community 70`, `Community 76`, `Community 77`, `Community 78`, `Community 85`, `Community 86`, `Community 89`, `Community 94`, `Community 95`, `Community 96`, `Community 98`, `Community 101`, `Community 104`, `Community 106`, `Community 110`, `Community 111`, `Community 118`, `Community 122`?**
  _High betweenness centrality (0.384) - this node is a cross-community bridge._
- **Why does `RuntimeFacade` connect `Infrastructure Adapters & App Host` to `BrainCore Orchestrator`, `Rule Planner & Skill Seeding`, `Planner Contracts & BrainContext`, `Skill Runtime Persistence`, `Legacy Session Dispatch`, `DI Container Resolvers`, `Runtime Pipeline Orchestrator`, `Workspace Memory Manager`, `Community 146`, `Community 150`, `Community 151`, `Community 152`, `AudioLoop / Gemini Live`, `Capability Matching`, `Community 33`, `Community 36`, `Community 165`, `Community 166`, `Community 41`, `Community 170`, `Community 43`, `Community 44`, `Community 51`, `Community 52`, `Community 53`, `Community 62`, `Community 63`, `Community 66`, `Community 70`, `Community 73`, `Community 76`, `Community 78`, `Community 85`, `Community 89`, `Community 91`, `Community 96`, `Community 101`, `Community 106`, `Community 108`, `Community 110`, `Community 111`, `Community 114`, `Community 118`, `Community 120`, `Community 122`, `Community 123`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Why does `DependencyContainer` connect `Infrastructure Adapters & App Host` to `BrainCore Orchestrator`, `Rule Planner & Skill Seeding`, `Planner Contracts & BrainContext`, `Skill Runtime Persistence`, `Community 136`, `Legacy Session Dispatch`, `Context Builder`, `Runtime Pipeline Orchestrator`, `Workspace Memory Manager`, `Community 146`, `Capability Matching`, `Community 25`, `Community 26`, `Community 28`, `Community 32`, `Community 33`, `Community 34`, `Community 163`, `Community 36`, `Community 165`, `Community 166`, `Community 39`, `Community 40`, `Community 43`, `Community 44`, `Community 49`, `Community 51`, `Community 52`, `Community 53`, `Community 56`, `Community 60`, `Community 61`, `Community 62`, `Community 64`, `Community 65`, `Community 66`, `Community 69`, `Community 70`, `Community 76`, `Community 77`, `Community 78`, `Community 82`, `Community 85`, `Community 91`, `Community 94`, `Community 95`, `Community 96`, `Community 101`, `Community 105`, `Community 108`, `Community 111`, `Community 118`, `Community 119`, `Community 122`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 306 inferred relationships involving `Bootstrapper` (e.g. with `run_tests()` and `ApplicationHost`) actually correct?**
  _`Bootstrapper` has 306 INFERRED edges - model-reasoned connections that need verification._
- **Are the 260 inferred relationships involving `DependencyContainer` (e.g. with `DummyAudioLoop` and `DummyMemoryStore`) actually correct?**
  _`DependencyContainer` has 260 INFERRED edges - model-reasoned connections that need verification._
- **Are the 167 inferred relationships involving `RuntimeFacade` (e.g. with `run_tests()` and `run_tests()`) actually correct?**
  _`RuntimeFacade` has 167 INFERRED edges - model-reasoned connections that need verification._
- **Are the 125 inferred relationships involving `BrainRequest` (e.g. with `BrainCore` and `ContextBuilder`) actually correct?**
  _`BrainRequest` has 125 INFERRED edges - model-reasoned connections that need verification._