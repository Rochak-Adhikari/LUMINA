# ADR-0016 — Skill Runtime: Dependency Resolution (Phase 8.3)

**Status:** Accepted · Dormant
**Date:** 2026-07-20
**Amends:** ADR-0015 (Capability Matching)

## Context

Phase 8.2 ranks candidate skills for a capability. Before any skill loads or
executes, the runtime must confirm the chosen candidate is actually **ready** —
registered, installed, capability-permitted, and running under acceptable grants.
That gate is Dependency Resolution.

## Decision

Add `DependencyResolver` (impl of `IDependencyResolver`) to `brain/skill_runtime/`.

- **Input:** the Phase 8.2 `CapabilityMatchResult` + caller-supplied grants
  (`granted_permissions`, `runtime_version`, `available_capabilities`).
- **Output:** immutable `DependencyResolution` (with `DependencyRequirement`
  checklist).
- Selects the **highest-ranked match whose every requirement is satisfied**
  (match order is already deterministic); falls back down the ranked list; if
  none qualifies, `resolved=False`, `skill=None`.
- Depends only on Phase 8.2 output — no Registry / RegistryEntry / skill_creator
  import. Pure + deterministic: no I/O, clocks, uuids, randomness, loading, or
  execution.

### Requirements checked (on the read-only DiscoveredSkill surface)

| kind | rule |
|------|------|
| registration | `registration_status == "registered"` |
| install | `installed_location` non-empty |
| capability | `skill_family ∈ available_capabilities` (when supplied) |
| runtime | `runtime_version` supplied → recorded satisfied (see deferral) |
| permission | each `granted_permissions` entry recorded as an allowed grant |

## Deferrals (flagged, consistent with ADR-0015)

The frozen Phase 7 `RegistryEntry` projection carries no `required_permissions`,
`minimum_version`, or declared-dependency list. Therefore:

- **Permission enforcement** (granted vs *required*) is deferred to the Sandbox
  (Phase 8.4) — 8.3 only records the grants.
- **Version constraints** are deferred to Phase 8.9 — a supplied
  `runtime_version` is recorded satisfied (no minimum to compare against).

Enriching these would require touching frozen Phase 7 artifacts (out of scope);
the correct future fix is to extend the Phase 8.1 discovery projection.

## Consequences

- Pipeline deepens: discovery → matching → **resolution** → (load/execute later).
- Phase 5–7 untouched, byte-identical; resolver dormant in DI +
  `RuntimeFacade.dependency_resolver`.
- 8.4 (Sandbox) consumes the resolved `DiscoveredSkill` + recorded grants.

## Verification

`tests/test_phase_8_step3.py` (19 tests). Full regression **753 PASS**.
