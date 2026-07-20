# Pipeline Stage 16 — Skill Executor (Phase 8.6)

**Package:** `brain/skill_runtime/`
**Service:** `SkillExecutor` (impl of `ISkillExecutor`)
**Output:** `ExecutionResult` (frozen, arbitrary output allowed)
**Status:** Dormant (DI-registered, no runtime consumer yet)

## Purpose

First stage that actually runs a loaded skill. Calls the canonical
`run(context)` exactly once and captures the outcome. No retries, recovery,
chaining, or orchestration.

## Contract

```
execute(loaded: LoadedSkill, context=None) -> ExecutionResult
```

## Data flow

```
LoadedSkill (stage 15)  +  context
      |
      v
SkillExecutor
      |  validate loaded + instance present
      |  resolve entrypoint (run canonical; legacy execute shim)
      |  call run(context) ONCE
      |  capture return / exception
      v
ExecutionResult { succeeded, output?, registry_key, error }
```

## Canonical interface

`run(context)` is the single runtime execution interface. A skill with only
legacy `execute` is bridged by a minimal shim. No permanent dual interface.

## Errors (never propagate)

| condition | error |
|-----------|-------|
| not loaded / no instance | `not_loaded` |
| no run/execute | `no_entrypoint` |
| skill raises | `execution_failed: <Type>` |

## Guarantees

- **8.5-only dependency** — never imports Registry / RegistryEntry /
  skill_creator / loader.
- Runs exactly once per call; no retries, recovery, chaining, planning,
  sandboxing, memory injection, scheduling, or async infrastructure.
- Exceptions captured into `ExecutionResult`; runtime never crashes.

## Deferred

Context injection → 8.7; failure recovery/retry → 8.8; version resolution → 8.9;
chaining → 8.10. See ADR-0019.

## Access

- DI: `ISkillExecutor` / `SkillExecutor`
  (`core/bootstrap.py::_register_skill_executor`, dormant).
- Facade: `RuntimeFacade.skill_executor`.

## Verification

`tests/test_phase_8_step6.py` — 17 tests. Regression **802 PASS**. ADR-0019.
