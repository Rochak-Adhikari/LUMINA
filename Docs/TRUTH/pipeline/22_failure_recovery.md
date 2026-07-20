# Pipeline Stage 22 — Failure Recovery (Phase 8.12)

**Package:** `brain/skill_runtime/`
**Service:** `FailureRecovery` (impl of `IFailureRecovery`)
**Output:** `RecoveryPlan` (frozen)
**Status:** Dormant (DI-registered, no runtime consumer yet)

## Purpose

First component that reasons about a failed pipeline run. Consumes the Stage 21
`RuntimePipelineResult` and returns a descriptive plan naming WHAT recovery
should happen. Analysis only — performs nothing (mirrors the Evolution Engine).

## Contract

```
plan(result: RuntimePipelineResult) -> RecoveryPlan
```

## Data flow

```
RuntimePipelineResult
   |  completed run          → needed=False, strategy="none"
   |  failed run (reason X)  → fixed reason→strategy table
   v
RecoveryPlan { needed, completed, failed_stage, registry_key,
               strategy, retryable, rationale }
```

## Recovery table

| pipeline reason | strategy | retryable |
|-----------------|----------|-----------|
| (completed) | `none` | no |
| `discovery_empty` | `review_required` | no |
| `no_match` | `rematch_capability` | no |
| `unresolved` | `review_required` | no |
| `sandbox_denied` | `abort` | no |
| `load_failed` | `retry_transient` | yes |
| `context_not_prepared` | `review_required` | no |
| `execution_failed` | `retry_transient` | yes |
| (unknown reason) | `none` | no |

## Guarantees

- **Descriptive only** — names recovery; never retries, re-invokes, executes,
  loads, loops, or branches into orchestration.
- **Interfaces-only** — depends only on skill_runtime interfaces + models.
- **No IO / no clocks / no retries / no threads** — no subprocess/threading/
  asyncio/importlib; no eval/exec/open/.now.
- **Inward dependency** — no stage (incl. the 8.11 orchestrator) depends on
  FailureRecovery.
- **Deterministic** — pure function of the input reason → identical plan.

## Access

- DI: `IFailureRecovery` / `FailureRecovery`
  (`core/bootstrap.py::_register_failure_recovery`, dormant).
- Facade: `RuntimeFacade.failure_recovery`.

## Note

Nothing calls it automatically; acting on a `RecoveryPlan` is a future gated
decision.

## Verification

`tests/test_phase_8_step12.py` — 11 tests. Regression **889 PASS**. ADR-0025.
