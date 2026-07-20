# ADR-0024 — Skill Runtime: Runtime Pipeline Orchestrator (Phase 8.11)

**Status:** Accepted · Dormant
**Date:** 2026-07-20
**Amends:** ADR-0016–ADR-0023 (the ten runtime stages)

## Context

Phases 8.1–8.10 built ten independent, immutable runtime stages (discovery →
matching → resolution → sandbox → loader → context injection → executor →
observer → recorder → persistence). Each was testable alone but nothing tied
them together. Phase 8.11 introduces the first component that understands the
complete chain — a pure coordinator.

## Decision

Add `RuntimePipeline` (impl of `IRuntimePipeline`) to `brain/skill_runtime/`.

- **Input:** the minimal inputs each existing stage needs (`CapabilityRequest`,
  `SandboxPolicy`, query, grants, snapshots, caller `metadata`/`timestamp`/
  `storage_key`). **Output:** immutable `RuntimePipelineResult` carrying every
  completed stage's artifact + a `reason`.
- **Coordination only:** calls the ten stages in order; each stage receives the
  previous stage's output. It contains NO business logic, duplicates nothing,
  inspects no internals, mutates no output.
- **Fail-fast:** on the first failing stage it stops and returns, populating the
  stages completed so far and propagating the failure `reason`
  (`discovery_empty`, `no_match`, `unresolved`, `sandbox_denied`, `load_failed`,
  `context_not_prepared`, `execution_failed`). On `execution_failed` the observer
  → recorder → persistence tail still runs so a failed execution is recorded.
- **Constructor-injected** stage interfaces — no service locator, no container
  access, no upward imports. Depends only on skill_runtime interfaces + models.

### Determinism

No clocks/randomness/IO/threads/retries. `RuntimePipelineResult` is
`ConfigDict(frozen=True, arbitrary_types_allowed=True)`. Same inputs + same
stage fakes → identical result.

## Consequences

- Pipeline: discovery → … → persistence, now coordinated by one orchestrator.
- Each stage remains independently testable; **no stage depends on
  RuntimePipeline** (dependency points inward only).
- Phase 5–7 untouched, byte-identical; orchestrator dormant in DI +
  `RuntimeFacade.runtime_pipeline`. Nothing calls it automatically.

## Verification

`tests/test_phase_8_step11.py` (14 tests). Full regression **878 PASS**.
