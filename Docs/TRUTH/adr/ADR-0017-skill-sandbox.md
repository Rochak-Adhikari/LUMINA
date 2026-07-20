# ADR-0017 — Skill Runtime: Skill Sandbox (Phase 8.4)

**Status:** Accepted · Dormant
**Date:** 2026-07-20
**Amends:** ADR-0016 (Dependency Resolution)

## Context

Before a resolved skill loads (8.5) or executes (8.6), the runtime must decide
whether it is *allowed* to run under current policy. Phase 8.4 is that first
execution-safety layer — a pure gatekeeper.

## Decision

Add `SkillSandbox` (impl of `ISkillSandbox`) to `brain/skill_runtime/`.

- **Input:** Phase 8.3 `DependencyResolution` + a `SandboxPolicy`
  (`allowed_permissions`, `require_resolved`, `max_risk`).
- **Output:** immutable `SandboxDecision` (`approved`, `skill?`, `violations`,
  `reason`).
- **Purely a gatekeeper** — never loads, imports, or executes; never touches the
  Registry / RegistryEntry / skill_creator. Depends only on 8.3 output + policy.
  Pure + deterministic (no I/O, clocks, entropy, mutation).

### Checks

1. `require_resolved` → `resolution.resolved` must be True; a skill must be present.
2. Each recorded **permission** requirement must be in `policy.allowed_permissions`
   (outside → `permission_denied:<value>` violation).
3. Any requirement already marked unsatisfied → `unsatisfied:<value>` violation.

Approved only when no violations.

## Deferrals (flagged, consistent with ADR-0015/0016)

The frozen Phase 7 `RegistryEntry` projection carries no risk field, so
`policy.max_risk` is **informational only** — no risk-tier comparison is made.
Actual permission *enforcement at execution* remains the executor's concern
(8.6); 8.4 gates on the recorded grants vs the policy allowlist. Enriching risk
data would require touching frozen Phase 7 artifacts (out of scope).

## Consequences

- Pipeline: discovery → matching → resolution → **sandbox** → (load/execute).
- Phase 5–7 untouched, byte-identical; sandbox dormant in DI +
  `RuntimeFacade.skill_sandbox`.
- 8.5 (Loader) proceeds only on an approved `SandboxDecision`.

## Verification

`tests/test_phase_8_step4.py` (16 tests). Full regression **769 PASS**.
