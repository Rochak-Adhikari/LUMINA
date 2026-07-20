# ADR-0025 — Skill Runtime: Failure Recovery (Phase 8.12)

**Status:** Accepted · Dormant
**Date:** 2026-07-20
**Amends:** ADR-0024 (Runtime Pipeline Orchestrator)

## Context

Phase 8.11 gave the runtime a coordinator that runs the ten stages and returns a
`RuntimePipelineResult` carrying a failure `reason` when a run stops early.
Nothing yet interprets that failure. Phase 8.12 adds the first component that
reasons about a failed run — a **descriptive** recovery advisor, mirroring the
Evolution Engine's "decide WHAT, perform nothing" contract (ADR-0008).

## Decision

Add `FailureRecovery` (impl of `IFailureRecovery`) to `brain/skill_runtime/`.

- **Input:** the immutable `RuntimePipelineResult`. **Output:** immutable
  `RecoveryPlan` naming what recovery should happen.
- **Descriptive only:** it maps the pipeline `reason` through a fixed
  advisory table to a `strategy` from a closed vocabulary (`none`,
  `retry_transient`, `rematch_capability`, `review_required`, `abort`), a
  `retryable` flag, and a `rationale`. It NEVER retries, re-invokes the pipeline,
  executes, loads, loops, branches into orchestration, writes memory, or mutates
  the result. Acting on a plan is a future gated phase.
- **Completed run:** `needed=False`, `strategy="none"` — nothing to recover.
- **Unknown reason:** safe `none` default (no guessing).
- **Retryable** is True only for transient failure classes (`load_failed`,
  `execution_failed`); structural failures (`no_match`, `sandbox_denied`, …) are
  not retryable.
- Depends only on skill_runtime interfaces + models. No stage depends on it.

### Determinism

Pure function of the input `reason`: a static reason→strategy table, no clocks,
ids, entropy, hashing, threads, or I/O. `RecoveryPlan` is `ConfigDict(frozen=True)`.
Same input → identical plan.

## Consequences

- Pipeline gains an advisory layer: `RuntimePipelineResult → RecoveryPlan`
  (analysis, not action).
- Phase 5–7 untouched, byte-identical; 8.11 orchestrator unchanged and unaware of
  recovery (inward dependency preserved). Advisor dormant in DI +
  `RuntimeFacade.failure_recovery`. Nothing calls it automatically.

## Verification

`tests/test_phase_8_step12.py` (11 tests). Full regression **889 PASS**.
