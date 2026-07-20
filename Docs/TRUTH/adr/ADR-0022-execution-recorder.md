# ADR-0022 — Skill Runtime: Execution Recorder (Phase 8.9)

**Status:** Accepted · Dormant
**Date:** 2026-07-20
**Amends:** ADR-0021 (Execution Observer)

## Context

The observer (8.8) produces an `ExecutionObservation`. Before any future
persistence layer, the runtime needs a stable, persistence-ready record. Phase
8.9 provides that pure transformation — it prepares records but never persists.

## Decision

Add `ExecutionRecorder` (impl of `IExecutionRecorder`) to `brain/skill_runtime/`.

- **Input:** `ExecutionObservation` + caller data (`conversation_id`,
  `metadata`, `timestamp`). **Output:** immutable `ExecutionRecord`.
- Pure: never persists, logs, saves, learns, updates memory, executes, retries,
  reloads, or mutates the observation. Depends only on the observation +
  skill_runtime models.
- `not observed` → `recorded=False`, `reason="not_observed"`. Otherwise fields
  are copied directly from the observation; summary comes from the observation
  (never invented/enriched).

### Determinism

`metadata` is **deep-copied** (never aliased); `timestamp` is **caller-supplied**
and never generated (consistent with ADR-0021). No clocks, randomness, or IO.
`ExecutionRecord` is `ConfigDict(frozen=True)`.

## Consequences

- Pipeline: … execution observer → **execution recorder**.
- Phase 5–7 untouched, byte-identical; recorder dormant in DI +
  `RuntimeFacade.execution_recorder`.
- **Persistence is a future phase** — the recorder deliberately produces records
  only; nothing is written to disk/db.

## Verification

`tests/test_phase_8_step9.py` (17 tests). Full regression **850 PASS**.
