# Pipeline Stage 21 — Runtime Pipeline Orchestrator (Phase 8.11)

**Package:** `brain/skill_runtime/`
**Service:** `RuntimePipeline` (impl of `IRuntimePipeline`)
**Output:** `RuntimePipelineResult` (frozen)
**Status:** Dormant (DI-registered, no runtime consumer yet)

## Purpose

First component that understands the whole runtime chain. Coordinates the ten
existing stages (11–20) in order and returns one immutable result carrying every
completed stage's artifact. Pure coordination — no business logic.

## Contract

```
run(request: CapabilityRequest, *, policy: SandboxPolicy, query="",
    granted_permissions=None, runtime_version="", available_capabilities=None,
    conversation_id="", user_input="", memory_snapshot=None,
    workspace_snapshot=None, environment_snapshot=None, available_tools=None,
    variables=None, metadata=None, timestamp=None, storage_key="")
      -> RuntimePipelineResult
```

## Data flow

```
discovery → matching → resolution → sandbox → loader → context injection
   → executor → observer → recorder → persistence
      |  each stage fed the previous stage's output
      |  first failure → stop, populate completed stages, propagate reason
      |  execution_failed → observer→recorder→persistence tail still runs
      v
RuntimePipelineResult { completed, registry_key, <10 stage artifacts?>, reason }
```

## Stop reasons

| stage | reason |
|-------|--------|
| discovery empty | `discovery_empty` |
| no capability match | `no_match` |
| unresolved deps | `unresolved` |
| sandbox denied | `sandbox_denied` |
| loader failed | `load_failed` |
| context not prepared | `context_not_prepared` |
| executor failed | `execution_failed` (still recorded) |
| success | `""`, `completed=True` |

## Guarantees

- **Interfaces-only** — depends only on skill_runtime interfaces + models; stage
  services constructor-injected (no service locator/container access).
- **No business logic / no mutation** — never duplicates stage logic, inspects
  internals, or modifies a stage output.
- **No IO / no clocks / no retries / no threads** — no subprocess/threading/
  asyncio/importlib; no eval/exec/open/.now.
- **Inward dependency** — no stage depends on RuntimePipeline.
- **Deterministic** — same inputs + stage outputs → identical result.

## Access

- DI: `IRuntimePipeline` / `RuntimePipeline`
  (`core/bootstrap.py::_register_runtime_pipeline`, dormant).
- Facade: `RuntimeFacade.runtime_pipeline`.

## Note

Nothing calls it automatically; wiring into a real runtime path is a future
decision.

## Verification

`tests/test_phase_8_step11.py` — 14 tests. Regression **878 PASS**. ADR-0024.
