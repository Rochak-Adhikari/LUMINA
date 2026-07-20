# ADR-0014 — Skill Runtime: Registry Discovery (Phase 8.1)

**Status:** Accepted · Dormant
**Date:** 2026-07-20
**Supersedes:** none · **Amends:** none

## Context

Phase 7 (Skill Creator) produces **immutable artifacts** — the terminal one being
a `RegistryEntry` appended to the append-only `BlueprintRegistry`. Phase 8 (Skill
Runtime) is the consumer: it discovers, matches, loads, and (later) executes
installed skills. The runtime must never modify Phase 7, never execute skills
directly from disk, and never bypass the Registry — **every flow begins from a
`RegistryEntry`.**

The first runtime question the Planner must ask is *"what skills exist?"* — and
it must ask it **without importing skills directly**. That coupling is exactly
what a runtime discovery service exists to break.

> **Roadmap note:** `ENGINEERING_ROADMAP.md` reserves the label "Phase 8.0 —
> Autonomous Planning". The owner directive re-scopes Phase 8 to **Skill
> Runtime** (consume installed skills). This ADR records that intentional
> re-scope; the roadmap entry is annotated rather than rewritten to preserve
> traceability.

## Decision

Introduce `brain/skill_runtime/` with a single read-only discovery service:

- **`IRegistryDiscovery.discover(query="") -> RegistrySearchResult`** — the
  contract the Planner resolves via DI.
- **`RegistryDiscovery`** — duck-typed over the registry (only `.entries()` is
  called), so Phase 8 has **no import of `BlueprintRegistry`** and no upward
  dependency on Phase 7.
- Immutable outputs **`DiscoveredSkill`** (read-only projection of a
  `RegistryEntry`; primitive fields only, no executable payload, no reference to
  the entry object) and **`RegistrySearchResult`**.

### Rules

1. **Read-only.** Discovery never registers, installs, mutates, or executes.
2. **Registry is the only source.** No disk scan, no skill import.
3. **Supersession without mutation.** Latest appended entry per `registry_key`
   wins (matches `BlueprintRegistry.get`); a later skipped/unregistered entry
   correctly hides an earlier registered one.
4. **Only `registered` entries are visible.**
5. **Deterministic.** Ordered by `(skill_family, package_name, registry_key)`,
   independent of insertion order. No clocks, identifiers, entropy, or I/O.
6. **Dormant.** Registered in DI + exposed on `RuntimeFacade.registry_discovery`;
   no runtime path wires into it yet.

## Consequences

- Planner ↔ skills decoupling is established at the discovery boundary.
- Phase 7 stays frozen and byte-identical; runtime behaviour unchanged (dormant).
- Future 8.2 (Capability Matching) consumes `RegistrySearchResult` — deterministic
  input for deterministic ranking.

## Verification

`tests/test_phase_8_step1.py` (19 tests). Full Phase 5+6+7+8 regression: **713 PASS**.
