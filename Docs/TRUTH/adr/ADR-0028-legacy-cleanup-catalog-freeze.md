# ADR-0028 — Phase 9.0 Legacy Cleanup: Catalog Truth-Mirror & the Phase-5 Freeze Boundary

**Status:** Accepted
**Date:** 2026-07-20
**Phase:** 9.0.2 (resolves Blocker B1 before any removals)
**Amends interpretation of:** Phase 5.4 freeze (does NOT alter Phase-5 behavior)
**Governance:** Append-only. Frozen Phases 5–8 behavior preserved.

## Context

Phase 9.0 removes CAD, Printer, and Kasa from the legacy tool system. The 9.0.1
audit surfaced Blocker B1: the removable tools appear in frozen Phase-5 artifacts —
`brain/skills/builtin.py::BUILTIN_SKILLS` (7 of 19 SkillSpecs) and the pinning
suite `tests/test_phase_5_4.py`. Naively, editing either violates the Phase-5
freeze.

Closer reading resolves the tension:

1. `builtin.py`'s docstring defines `BUILTIN_SKILLS` as declarations
   *"regenerated from the LIVE legacy registries so every provider_ref names a
   real, dispatchable tool."* It is a **runtime-derived mirror** of the live
   tool set, not frozen logic.
2. `test_phase_5_4.py` enforces the invariant **catalog ≡ live registry**:
   - `test_full_tier1_coverage` (:74) asserts a **dynamic bijection**
     `{provider_ref of _TIER1_SKILLS} == ToolDispatcherRegistry.keys()`,
     computed live — it self-adjusts when tools are removed in lockstep.
   - `test_every_provider_ref_is_real` (:55) requires every spec to name a live
     tool.
   - The **only** hardcoded number is `test_skill_registry_still_19` (:577).
3. The removable tools are **not** referenced as behavioral dependencies
   elsewhere in frozen code. `brain/test_phase_1_2.py:264,356` and
   `brain/events.py:24` use `"generate_cad"` only as an arbitrary string literal.
   Phases 6/7/8 consume `RegistryEntry`, never these legacy specs.

Correction to 9.0.1: `BUILTIN_SKILLS` is **19** (16 tier-1 + 3 tier-2), not 31.

## Decision

The Phase-5.4 freeze protects **behavior** (planning determinism, BrainCore
pass-through, DI wiring semantics, dispatch parity), **not** the runtime-derived
mirror data. Specifically:

- `brain/skills/builtin.py::BUILTIN_SKILLS` membership and the hardcoded pinning
  **counts** in `tests/test_phase_5_4.py` are classified as *runtime-derived
  mirror data*.
- The frozen invariant is the **relationship** `catalog ≡ live legacy registry`,
  enforced by the pinning tests — not a fixed membership or count.
- Synchronizing the mirror + counts in lockstep with an **ADR-authorized
  Phase-9 removal maintains** that invariant. It is therefore permitted and is
  **not** a freeze violation.

This principle is **reusable** for all subsequent Phase-9 milestones that alter
the legacy catalog (9.0.3–9.0.5 removals; later migration phases).

### Scope guardrail (narrow, to prevent abuse)

The reinterpretation applies ONLY to:
(a) `BUILTIN_SKILLS` membership, and
(b) hardcoded catalog/service **counts** in `test_phase_5_4.py`,
and ONLY to track an ADR-authorized runtime change.

Every frozen **behavioral** assertion remains untouchable. No other frozen file,
no Phase 6/7/8 code, and no planning/determinism/DI-semantics test may be edited
under this ADR.

## Rationale

- **Truthfulness:** a catalog that advertises tools the runtime cannot dispatch
  is a latent defect (a planner could emit an undispatchable `skill_id`). Keeping
  the mirror honest is the safer state.
- **Lockstep is self-verifying:** the dynamic bijection test passes iff specs and
  handlers are removed together, making incomplete removals fail loudly.
- **One principle, not N exceptions:** every Phase-9 catalog change would
  otherwise require a fresh "frozen exception." This ADR draws the line once.

## Alternatives Rejected

- **A — Leave removed tools as inert metadata.** Breaks
  `test_full_tier1_coverage`, `test_every_provider_ref_is_real`, and
  `test_tier1_specs_point_at_tool_dispatcher`; leaves a lying catalog. Worse for
  the freeze than a lockstep update. Rejected.
- **B — One-off narrow exception (this edit only).** Correct mechanics but
  re-litigated at every future removal. Subsumed by D's reusable principle.
- **C — Compatibility shim (no-op stub handlers).** Contradicts 9.0's removal
  mandate, adds a permanent stub layer, and keeps retired tools offered to the
  model. Rejected.

## Consequences

- 9.0.3–9.0.5 may remove the 7 SkillSpecs from `builtin.py` in lockstep with
  their tier-1 handlers/agents, and update the one hardcoded count
  `test_skill_registry_still_19` (19 → 12 after all three systems removed).
- The dynamic bijection and real-ref tests continue to pass automatically.
- Frozen Phase-5 behavior is byte-identical; only mirror data changes.
- Rollback = git revert of the removal commit(s); small and localized.

## Migration Impact (post-removal target state)

- `_TIER1_SKILLS`: 16 → 9 (remove `generate_cad`, `iterate_cad`,
  `discover_printers`, `print_stl`, `get_print_status`, `list_smart_devices`,
  `control_light`).
- `_TIER2_SKILLS`: 3 (unchanged).
- `BUILTIN_SKILLS`: 19 → 12.
- `ToolDispatcherRegistry`: 16 → 9 handler keys (bijection preserved: 9 == 9).
- `test_skill_registry_still_19`: assert 12.
- `test_metadata_registry_still_11`: verify `ISmartHomeAgent` is NOT among the 11
  (bootstrap skips it when `kasa_agent=None`, as in the test); expected
  unaffected — confirm during 9.0.3.

## Validation Requirements

- After each removal step, `tests/test_phase_5*.py` and the full Phase 5+6+7+8
  regression must pass with the updated count.
- The dynamic bijection (`test_full_tier1_coverage`) must pass without editing
  its logic — only lockstep data changes may make it pass.
- AST/grep proof: no surviving reference to a removed `skill_id`/`provider_ref`
  in `builtin.py` or the live registries.
- Zero diffs under frozen `brain/skill_runtime`, `brain/skill_creator`,
  `brain/evolution`, and no edit to any Phase-5 **behavioral** test.
