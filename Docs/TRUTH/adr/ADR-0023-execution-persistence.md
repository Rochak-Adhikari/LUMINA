# ADR-0023 — Skill Runtime: Execution Persistence (Phase 8.10)

**Status:** Accepted · Dormant
**Date:** 2026-07-20
**Amends:** ADR-0022 (Execution Recorder)

## Context

The recorder (8.9) produces a persistence-ready `ExecutionRecord`. Before any
actual storage layer, the runtime needs a stage that decides whether a record is
acceptable for persistence and wraps it. Phase 8.10 provides that prepare step —
it stores nothing.

## Decision

Add `ExecutionPersistence` (impl of `IExecutionPersistence`) to
`brain/skill_runtime/`.

- **Input:** `ExecutionRecord` + optional caller `storage_key`.
  **Output:** immutable `PersistenceResult`.
- `not recorded` → `persistable=False`, `reason="not_recorded"`. Otherwise the
  record is wrapped as-is with the caller-supplied `storage_key`.
- **NOT storage:** never writes files/db/sqlite/json, serializes, saves, or calls
  memory/vector-db/telemetry/event-bus/registry/planner/workspace/network.
  Depends only on the `ExecutionRecord` + skill_runtime models.

### Determinism

`storage_key` is caller-supplied and never generated — no hashes, UUIDs, or
timestamps. No IO. `PersistenceResult` is `ConfigDict(frozen=True)`.

## Consequences

- Pipeline: … execution recorder → **execution persistence (prepare)**.
- Phase 5–7 untouched, byte-identical; persistence dormant in DI +
  `RuntimeFacade.execution_persistence`.
- **Actual storage is a later phase** — this stage only prepares an immutable
  PersistenceResult for a future storage backend.

## Verification

`tests/test_phase_8_step10.py` (14 tests). Full regression **864 PASS**.
