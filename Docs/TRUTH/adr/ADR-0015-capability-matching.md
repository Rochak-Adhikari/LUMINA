# ADR-0015 — Skill Runtime: Capability Matching (Phase 8.2)

**Status:** Accepted · Dormant
**Date:** 2026-07-20
**Amends:** ADR-0014 (Skill Runtime: Registry Discovery)

## Context

Phase 8.1 gave the runtime a **descriptive** question — `RegistryDiscovery`
answers *"what skills exist?"*. The Planner needs a **semantic** question:
*"which of those skills satisfy this capability request?"* The Planner must never
search the registry directly; it asks the matcher, the matcher asks discovery.

## Decision

Add `CapabilityMatcher` (impl of `ICapabilityMatcher`) to `brain/skill_runtime/`.

- **Depends only on `IRegistryDiscovery`** (injected). No import of the Registry,
  `RegistryEntry`, `BlueprintRegistry`, or any `skill_creator` stage.
- Immutable inputs/outputs: `CapabilityRequest`, `CapabilityMatch`,
  `CapabilityMatchResult` (all frozen, no executable payload, no `RegistryEntry`).
- Pure + deterministic: no I/O, disk, network, clocks, uuids, randomness,
  hashing, loading, execution, or side effects.

### Matching (deterministic, metadata-only)

Operates on the read-only `DiscoveredSkill` projection. Priority high → low:

| Score | Rule |
|------|------|
| 100 | exact capability (`capability == skill_family`) |
| 80  | alias (capability substring of `semantic_fingerprint` or `package_name`) |
| 60  | tag (a requested tag appears in family / package / fingerprint) |

`family` and `package` are hard restrictions applied before scoring. A request
with neither capability nor tags is a pure filter (survivors returned at score 0).
Ordering: score desc, then `skill_family`, `package_name`, `registry_key`.

## Known limitation (flagged, not worked around)

The frozen Phase 7 `RegistryEntry` — and therefore the 8.1 `DiscoveredSkill`
projection — carries **no** `provided_capabilities`, `skill_dna` (tags), or
`version`. Those live on `SkillBlueprint` and were deliberately not projected
into the terminal artifact. Consequences:

- Matching uses the projected identity surface (family / package / fingerprint),
  not the blueprint's declared capability/tag lists.
- `CapabilityRequest.version_preference` is accepted but **inert** — version
  ranking is deferred to Phase 8.9 (Version Resolution).

Enriching the projection would require touching frozen Phase 7 artifacts, which
is out of scope. If richer matching is later required, the correct fix is to
extend the **8.1 discovery projection** (Phase 8, mutable), never `RegistryEntry`.

## Consequences

- Planner ↔ registry decoupling deepens: Planner → matcher → discovery → registry.
- Phase 5–7 untouched, byte-identical; matcher dormant in DI +
  `RuntimeFacade.capability_matcher`.
- 8.3 (Dependency Resolution) consumes `CapabilityMatchResult`.

## Verification

`tests/test_phase_8_step2.py` (21 tests). Full regression **734 PASS**.
