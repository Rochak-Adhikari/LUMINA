# Pipeline Stage 20 — Execution Persistence (Phase 8.10)

**Package:** `brain/skill_runtime/`
**Service:** `ExecutionPersistence` (impl of `IExecutionPersistence`)
**Output:** `PersistenceResult` (frozen)
**Status:** Dormant (DI-registered, no runtime consumer yet)

## Purpose

Prepare step for persistence — decides whether an `ExecutionRecord` is
acceptable for persistence and wraps it into an immutable `PersistenceResult`.
It stores nothing; actual storage is a later phase.

## Contract

```
prepare(record: ExecutionRecord, *, storage_key: str = "") -> PersistenceResult
```

## Data flow

```
ExecutionRecord (stage 19)  +  caller storage_key
      |
      v
ExecutionPersistence
      |  recorded? no → persistable=False, reason=not_recorded
      |  wrap record as-is + caller storage_key
      v
PersistenceResult { persistable, record?, storage_key, reason }
```

## Guarantees

- **Record-only dependency** — never imports memory, workspace, planner,
  registry, loader, executor, observer, recorder, sandbox, context_injector,
  skill_creator, runtime_facade, or event_bus.
- **NOT storage / no IO / no serialization** — no os/pathlib/sqlite3/subprocess/
  threading/asyncio/logging/json/pickle/importlib/requests/socket; no
  open/write/dumps/dump/eval/exec.
- **Deterministic** — storage_key caller-supplied (never generated: no hash/uuid/
  timestamp); input never mutated.

## Errors

| condition | reason |
|-----------|--------|
| record not recorded | `not_recorded` |

## Access

- DI: `IExecutionPersistence` / `ExecutionPersistence`
  (`core/bootstrap.py::_register_execution_persistence`, dormant).
- Facade: `RuntimeFacade.execution_persistence`.

## Note

Actual storage (writing to disk/db/vector store) is a future phase; this stage
only prepares an immutable PersistenceResult.

## Verification

`tests/test_phase_8_step10.py` — 14 tests. Regression **864 PASS**. ADR-0023.
