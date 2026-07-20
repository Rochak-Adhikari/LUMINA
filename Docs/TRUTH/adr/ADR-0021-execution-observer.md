# ADR-0021 — Skill Runtime: Execution Observer (Phase 8.8)

**Status:** Accepted · Dormant
**Date:** 2026-07-20
**Amends:** ADR-0019 (Skill Executor)

## Context

The executor produces an `ExecutionResult`. Later systems (telemetry, evolution
analysis) need a descriptive record of what happened — without the observer ever
influencing execution. Phase 8.8 provides that purely observational stage.

## Decision

Add `ExecutionObserver` (impl of `IExecutionObserver`) to `brain/skill_runtime/`.

- **Input:** `ExecutionResult`. **Output:** immutable `ExecutionObservation`.
- Purely observational: never executes, retries, modifies output/memory, logs
  externally, touches disk, or calls services. Depends only on the
  `ExecutionResult` + skill_runtime models.
- `ExecutionObservation` fields: `observed`, `registry_key`, `succeeded`,
  `error`, `output_type` (result output's type name; "NoneType" when absent),
  `timestamp`, `summary` (short deterministic sentence).

### Determinism vs. timestamp (flagged)

The spec lists a `timestamp` field. To preserve the runtime's determinism rule
(no inline clock reads — a generated timestamp would break reproducibility), the
`timestamp` is **caller-supplied** (Optional, None by default) and NEVER
generated inside the observer. This mirrors the deferral pattern in ADR-0015/0016
(supplied-not-generated time). The `datetime` import is permitted by the spec but
unused — the observer generates no time.

## Consequences

- Pipeline: … executor → **execution observer**.
- Phase 5–7 untouched, byte-identical; observer dormant in DI +
  `RuntimeFacade.execution_observer`.
- No retries/recovery here (that is 8.8's sibling scope in the original 8.8
  "Failure Recovery" naming — this milestone is scoped strictly to observation
  per the directive).

## Verification

`tests/test_phase_8_step8.py` (16 tests). Full regression **833 PASS**.
