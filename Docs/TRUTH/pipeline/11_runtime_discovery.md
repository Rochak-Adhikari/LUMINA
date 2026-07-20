# Pipeline Stage 11 — Runtime Discovery (Phase 8.1)

**Package:** `brain/skill_runtime/`
**Service:** `RegistryDiscovery` (impl of `IRegistryDiscovery`)
**Output:** `RegistrySearchResult` (frozen)
**Status:** Dormant (DI-registered, no runtime consumer yet)

## Purpose

Stage 11 is the **first Skill Runtime stage** and the boundary between "skills
produced" (Phase 7) and "skills consumed" (Phase 8). It answers *"what skills
exist?"* so the Planner discovers skills through DI instead of importing them.

Where stages 01–10 each **write** an immutable artifact into the pipeline,
stage 11 **reads** the terminal artifact (`RegistryEntry`, produced by stage 07)
and projects it into a runtime-facing catalog.

## Contract

```
discover(query: str = "") -> RegistrySearchResult
```

- `query=""` → list every registered skill.
- Non-empty `query` → case-insensitive substring match over
  `skill_family` / `package_name` / `semantic_fingerprint`.

## Data flow

```
BlueprintRegistry (Phase 7, frozen, append-only)
        |  .entries()   (duck-typed; no BlueprintRegistry import)
        v
RegistryDiscovery
        |  filter: latest-per-key, registered-only
        |  project: RegistryEntry -> DiscoveredSkill (metadata only)
        |  sort: (family, package, key)
        v
RegistrySearchResult { skills[], total_count, query }
```

## Immutable output — `DiscoveredSkill`

Read-only projection; primitive fields copied out of a `RegistryEntry`. Carries
**no executable code** and **no reference** to the entry object, so the frozen
Phase 7 catalog cannot be mutated through it:

`blueprint_id · recommendation_id · semantic_fingerprint · skill_family ·
package_name · registry_key · installed_location · registration_status`

## Guarantees

- **Read-only** — never registers, installs, mutates, or executes.
- **Registry-only** — no disk scan, no skill import.
- **Supersession without mutation** — latest appended entry per key wins;
  a later non-registered entry hides an earlier registered one.
- **Deterministic** — stable ordering, no clocks/identifiers/entropy/I/O.

## Access

- DI: `IRegistryDiscovery` / `RegistryDiscovery` (registered in
  `core/bootstrap.py::_register_skill_runtime`, dormant).
- Facade: `RuntimeFacade.registry_discovery`.

## Verification

`tests/test_phase_8_step1.py` — 19 tests. Regression **713 PASS**. ADR-0014.
