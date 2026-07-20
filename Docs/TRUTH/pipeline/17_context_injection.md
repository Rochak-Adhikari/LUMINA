# Pipeline Stage 17 — Context Injection (Phase 8.7)

**Package:** `brain/skill_runtime/`
**Service:** `ContextInjector` (impl of `IContextInjector`)
**Output:** `ContextInjectionResult` wrapping a frozen `ExecutionContext`
**Status:** Dormant (DI-registered, no runtime consumer yet)

## Purpose

Prepares everything a skill needs before execution as immutable data. Sits
between the loader (15/16 loader→executor) and the executor: loader → **context
injection** → executor.

## Contract

```
inject(loaded: LoadedSkill, *, conversation_id="", user_input="",
       memory_snapshot=None, workspace_snapshot=None, environment_snapshot=None,
       available_tools=None, variables=None, metadata=None)
    -> ContextInjectionResult
```

## Data flow

```
LoadedSkill (stage 15)  +  caller data
      |
      v
ContextInjector
      |  validate loaded + skill present
      |  copy snapshots/variables/metadata (inputs never mutated)
      |  build frozen ExecutionContext (registry_key from skill identity only)
      v
ContextInjectionResult { prepared, context?, reason }
```

## ExecutionContext (frozen)

`registry_key`, `conversation_id`, `user_input`, `memory_snapshot`,
`workspace_snapshot`, `environment_snapshot`, `available_tools`, `variables`,
`metadata`. Plain read-only data — no live services, no runtime objects, no raw
skill instance.

## Guarantees

- **Pure transformation** — no load, execute, retry, recover, chain, schedule,
  registry access, memory write, tool/network/subprocess.
- **Inputs never mutated** — supplied dicts copied, not aliased.
- **Does not read the raw instance** — only the skill's registry_key crosses in.
- Depends only on LoadedSkill + caller data + skill_runtime models.

## Errors

| condition | reason |
|-----------|--------|
| not loaded | `not_loaded` |
| no skill | `no_skill` |

## Access

- DI: `IContextInjector` / `ContextInjector`
  (`core/bootstrap.py::_register_context_injector`, dormant).
- Facade: `RuntimeFacade.context_injector`.

## Verification

`tests/test_phase_8_step7.py` — 15 tests. Regression **817 PASS**. ADR-0020.
