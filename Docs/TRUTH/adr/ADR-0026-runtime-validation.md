# ADR-0026 — Skill Runtime: Runtime Validation (Phase 8.13)

**Status:** Accepted · Dormant
**Date:** 2026-07-20
**Amends:** ADR-0025 (Failure Recovery)

## Context

Phase 8.11 produces a `RuntimePipelineResult` and Phase 8.12 advises recovery on
failure. Nothing yet asserts that a result is itself *structurally sound* — that
the right stage artifacts are present for the outcome and the completion/reason
flags agree with them. Phase 8.13 adds the first component that validates the
result's internal integrity — a **read-only** checker, mirroring the runtime's
descriptive-analysis contract (ADR-0008).

## Decision

Add `RuntimeValidator` (impl of `IRuntimeValidator`) to `brain/skill_runtime/`.

- **Input:** the immutable `RuntimePipelineResult`. **Output:** immutable
  `ValidationReport`.
- **Read-only:** asserts three deterministic invariants and reports violations.
  It NEVER repairs, re-runs, mutates, executes, or recovers. Acting on a failed
  validation is out of scope.
- **Invariants:**
  1. **contiguity** — the populated stage set is a gap-free prefix of the
     pipeline order (no artifact after a missing earlier stage).
  2. **completion** — `completed` is True iff all ten stages are populated AND
     `reason` is empty.
  3. **reason match** — a failed run's `reason` matches the last populated stage
     per the fixed stop-reason table; a completed run has an empty `reason`.
     `execution_failed` expects the full observer→recorder→persistence tail.
- **Violation codes** (ordered, deterministic): `noncontiguous_stages`,
  `completed_but_incomplete`, `completed_with_reason`, `failed_without_reason`,
  `unknown_reason`, `reason_stage_mismatch`.
- Depends only on skill_runtime interfaces + models. No stage depends on it.

### Determinism

Pure function of the input result: fixed stage-order tuple + fixed stop-reason
table, no clocks, ids, entropy, hashing, threads, or I/O. `ValidationReport` is
`ConfigDict(frozen=True)`. Same input → identical report.

## Consequences

- Pipeline gains an integrity-assertion layer: `RuntimePipelineResult →
  ValidationReport` (checking, not action).
- Phase 5–8.12 untouched, byte-identical; 8.11 orchestrator and 8.12 advisor
  unchanged and unaware of validation (inward dependency preserved). Validator
  dormant in DI + `RuntimeFacade.runtime_validator`. Nothing calls it automatically.

## Verification

`tests/test_phase_8_step13.py` (15 tests). Full regression **904 PASS**.
