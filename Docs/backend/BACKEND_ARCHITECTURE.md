# Backend Architecture

**Date:** 2026-07-20
Scope: describes the backend exactly as it exists today. Descriptive only.

## Stack

- **Python** backend (`backend/`), FastAPI + `python-socketio` (ASGI) server.
- **Gemini Live** audio/multimodal via `AudioLoop`.
- Frozen runtime core: DI container, EventBus, RequestPipeline, RuntimeFacade.

## Important folders

| Path | Role |
|------|------|
| `backend/server.py` | ASGI app: REST endpoints + Socket.IO events + startup/shutdown. ~3.3k lines. |
| `backend/lumina.py` | `AudioLoop` — Gemini Live session, tool-call loop, permission gate. |
| `backend/core/` | Runtime core: `container.py` (DI), `bootstrap.py` (composition root), `registry.py` (registries), `runtime_facade.py`, `interfaces.py`, `session.py`, `application.py`, `pipeline.py`, `metadata.py`, `legacy_dispatch.py`, `tool_handlers.py`. |
| `backend/brain/` | Cognitive layer: `core/` (BrainCore), `planning/`, `skills/`, `workspace/`, `reflection/`, `evolution/`, `skill_creator/`, `skill_runtime/`, `state.py`, `events.py`. |
| `backend/actions/` | Tier-2 action tools (`ACTION_REGISTRY`). |
| `backend/tools/` | Local + cloud browser control. |
| `backend/tests/` | pytest suites (Phase 5–8 = 913 tests). |

## Startup sequence

1. `server.py` module load: reads `settings.json` → `SETTINGS`, tool permissions.
2. Constructs `DependencyContainer` → `Bootstrapper(container=container)` → `bootstrap()`.
3. `Bootstrapper.bootstrap()` registers services in order:
   `brain_state → event_bus → memory_store → project_manager → memory_engine →
   execution_context_factory → pipeline → adapters → planning_and_skills →
   workspace_memory → reflection → evolution → brain_core → service_metadata`,
   then `ApplicationHost`.
   - Importing `core.tool_handlers` (side effect) populates `ToolDispatcherRegistry` (Tier-1).
   - `skill_creator` and `skill_runtime` register their stages **dormant**.
4. `RuntimeFacade(container)` exposes fresh-resolve accessors.
5. Uvicorn binds port 8000 (scans 8001–8009 only if occupied — Phase 4.1).
6. On first Socket.IO `start_audio`: `AudioLoop` constructed, attached to
   `SessionManager`, Gemini Live session opened, `legacy_executor` bound.

## Dependency Injection

- `core/container.py::DependencyContainer` — `register_instance` /
  `register_singleton` / `register_transient` / `resolve` / `is_registered`.
  Thread-safe, lazy. Singletons cached after first resolve.
- All services registered through `Bootstrapper`, never module globals.

## Registries

| Registry | Location | Contents |
|----------|----------|----------|
| `ToolDispatcherRegistry` | `core/registry.py` | **9** Tier-1 async handlers `handler(fc, loop)` (`core/tool_handlers.py`). |
| `ActionRegistry` → `ACTION_REGISTRY` | `core/registry.py`, `actions/__init__.py` | **18** Tier-2 sync actions `fn(params, response, player, memory_store)`. |
| `SkillRegistry` | `brain/skills/registry.py` | **12** `SkillSpec` metadata records (mirror of the two live registries; ADR-0028). |
| `ServiceMetadataRegistry` | `core/metadata.py` | **11** DI service descriptors. |
| `AgentRegistry`, `ToolRegistry` | `core/registry.py` | Defined, unused (dead). |

## RuntimeFacade

`core/runtime_facade.py` — single entry surface over the container. Accessors:
`brain_state_adapter`, `event_bus_adapter`, `pipeline`, `memory_manager`,
`workspace_manager`, `knowledge_manager`, `project_manager`, `brain_core`,
`planner`, `legacy_executor`, `application_host`, plus dormant Skill Runtime
accessors (`registry_discovery`, `capability_matcher`, `dependency_resolver`,
`skill_sandbox`, `skill_loader`, `skill_executor`, `context_injector`,
`execution_observer`, `execution_recorder`, `execution_persistence`,
`runtime_pipeline`, `failure_recovery`, `runtime_validator`).

## AudioLoop

`lumina.py::AudioLoop` — owns the Gemini Live session. Per session: streams
mic/video, receives audio + transcription, runs the two-tier tool loop
(Tier-1 `ToolDispatcherRegistry` → Tier-2 `ACTION_REGISTRY`), applies the
permission gate (`True` auto-run / `False` deny / absent → confirmation), and
drives UI callbacks (`on_*`). Constructed lazily on `start_audio`.

## Brain

- `BrainCore` — orchestration authority (plan → execute → reflect). Flag-gated
  (`brain_core_enabled`, default False) → runtime byte-identical when off.
- `PlannerChain` (RulePlanner → LLMPlanner) resolved as `IPlanner`.
- `SkillManager` + `SkillRegistry` execute a `Task` via `LegacyToolExecutor`
  (bound to `core/legacy_dispatch.build_session_dispatch` at session start).
- `evolution/`, `skill_creator/`, `skill_runtime/` — dormant analysis/runtime
  pipelines (Phases 6/7/8), consumed by no live path.

## Execution flow (voice tool call)

```
Gemini function_call
  → AudioLoop tool loop (lumina.py)
      permission gate
      Tier-1: ToolDispatcherRegistry.contains(name) → await handler(fc, loop)
      Tier-2: name in ACTION_REGISTRY → to_thread(fn, params, None, None, memory_store)
      else → explicit "unregistered" FunctionResponse
  → FunctionResponse back to Gemini
```

Brain path (dormant unless `brain_core_enabled`): `user_input` →
`BrainCore.handle` → PlannerChain → SkillManager → LegacyToolExecutor →
legacy_dispatch → same two-tier handlers.
