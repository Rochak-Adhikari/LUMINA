# Pipeline Stage 23 — Runtime Validation (Phase 8.13)

**Package:** `brain/skill_runtime/`
**Service:** `RuntimeValidator` (impl of `IRuntimeValidator`)
**Output:** `ValidationReport` (frozen)
**Status:** Dormant (DI-registered, no runtime consumer yet)

## Purpose

First component that asserts a pipeline result's structural integrity. Consumes
the Stage 21 `RuntimePipelineResult` and returns a report of invariant
violations. Read-only — checks and reports, performs nothing.

## Contract

```
validate(result: RuntimePipelineResult) -> ValidationReport
```

## Data flow

```
RuntimePipelineResult
   |  contiguity  — populated stages form a gap-free prefix
   |  completion  — completed iff all 10 stages populated AND reason empty
   |  reason match— failed reason ↔ last populated stage (fixed table)
   v
ValidationReport { valid, completed, checked, last_stage, violations }
```

## Stage order

```
discovery → match → resolution → sandbox → loaded → context
   → execution → observation → record → persistence
```

## Violation codes

| code | meaning |
|------|---------|
| `noncontiguous_stages` | an artifact appears after a missing earlier stage |
| `completed_but_incomplete` | completed=True but not all stages populated |
| `completed_with_reason` | completed=True but reason non-empty |
| `failed_without_reason` | completed=False but reason empty |
| `unknown_reason` | reason not in the fixed stop-reason table |
| `reason_stage_mismatch` | last populated stage ≠ reason's expected stage |

## Guarantees

- **Read-only** — asserts integrity; never repairs, re-runs, mutates, executes,
  or recovers.
- **Interfaces-only** — depends only on skill_runtime interfaces + models.
- **No IO / no clocks / no retries / no threads** — no subprocess/threading/
  asyncio/importlib; no eval/exec/open/.now.
- **Inward dependency** — no stage (incl. 8.11 orchestrator, 8.12 advisor)
  depends on RuntimeValidator.
- **Deterministic** — pure function of the input result → identical report.

## Access

- DI: `IRuntimeValidator` / `RuntimeValidator`
  (`core/bootstrap.py::_register_runtime_validator`, dormant).
- Facade: `RuntimeFacade.runtime_validator`.

## Note

Nothing calls it automatically; acting on a `ValidationReport` is a future gated
decision.

## Verification

`tests/test_phase_8_step13.py` — 15 tests. Regression **904 PASS**. ADR-0026.
