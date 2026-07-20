# Pipeline Stage 19 — Execution Recorder (Phase 8.9)

**Package:** `brain/skill_runtime/`
**Service:** `ExecutionRecorder` (impl of `IExecutionRecorder`)
**Output:** `ExecutionRecord` (frozen)
**Status:** Dormant (DI-registered, no runtime consumer yet)

## Purpose

Pure transformation of one `ExecutionObservation` into one persistence-ready
`ExecutionRecord`. Prepares records for a future persistence layer — persists
nothing itself.

## Contract

```
record(observation: ExecutionObservation, *, conversation_id="",
       metadata=None, timestamp=None) -> ExecutionRecord
```

## Data flow

```
ExecutionObservation (stage 18)  +  caller data
      |
      v
ExecutionRecorder
      |  observed? no → recorded=False, reason=not_observed
      |  copy metadata (deep, never aliased)
      |  carry summary/succeeded/output_type/error from observation
      |  attach caller-supplied conversation_id + timestamp
      v
ExecutionRecord { recorded, registry_key, conversation_id, summary, succeeded,
                  output_type, error, metadata, timestamp, reason }
```

## Guarantees

- **Observation-only dependency** — never imports registry, planner, workspace,
  memory, executor, loader, sandbox, context_injector, skill_creator,
  runtime_facade, or event_bus.
- **No persistence / no IO** — no os/pathlib/subprocess/threading/asyncio/
  importlib/logging/sqlite/requests/socket; no open/write/eval/exec.
- **Deterministic** — metadata deep-copied, timestamp caller-supplied (never
  generated), inputs never mutated.

## Errors

| condition | reason |
|-----------|--------|
| observation not observed | `not_observed` |

## Access

- DI: `IExecutionRecorder` / `ExecutionRecorder`
  (`core/bootstrap.py::_register_execution_recorder`, dormant).
- Facade: `RuntimeFacade.execution_recorder`.

## Note

Persistence (writing records to disk/db) is a future phase; this stage only
prepares immutable records.

## Verification

`tests/test_phase_8_step9.py` — 17 tests. Regression **850 PASS**. ADR-0022.
