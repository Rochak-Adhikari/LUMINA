# Pipeline Stage 12 — Capability Matching (Phase 8.2)

**Package:** `brain/skill_runtime/`
**Service:** `CapabilityMatcher` (impl of `ICapabilityMatcher`)
**Output:** `CapabilityMatchResult` (frozen)
**Status:** Dormant (DI-registered, no runtime consumer yet)

## Purpose

Stage 12 is the **semantic** runtime layer. Stage 11 (Registry Discovery) is
descriptive — *"what skills exist?"*. Stage 12 answers *"which of those skills
satisfy this capability request?"* so the Planner asks the matcher instead of
searching the registry.

## Contract

```
match(request: CapabilityRequest) -> CapabilityMatchResult
```

`CapabilityRequest`: `capability`, optional `family`, optional `package`,
optional `tags`, optional `version_preference` (inert — see limitation).

## Data flow

```
CapabilityRequest
      |
      v
CapabilityMatcher ── depends only on IRegistryDiscovery
      |  discovery.discover()  → DiscoveredSkill[]
      |  restrict: family / package (hard filters)
      |  score:   exact 100 / alias 80 / tag 60
      |  order:   score desc, family, package, registry_key
      v
CapabilityMatchResult { matches[CapabilityMatch], match_count, capability }
```

## Scoring

| Score | Rule |
|------|------|
| 100 | `capability == skill_family` (exact) |
| 80  | capability is a substring of `semantic_fingerprint` or `package_name` (alias) |
| 60  | a requested tag appears in family / package / fingerprint |
| 0   | pure filter (no capability, no tags) — survivors of family/package restriction |

## Guarantees

- **Discovery-only dependency** — never imports Registry / RegistryEntry /
  skill_creator.
- **Pure + deterministic** — no I/O, clocks, uuids, randomness, hashing,
  loading, or execution; identical inputs → identical output.
- **Read-only** — never mutates the registry or discovery results.

## Limitation

Matches on the projected `DiscoveredSkill` surface (family / package /
fingerprint). The frozen Phase 7 `RegistryEntry` exposes no
`provided_capabilities` / tags / version, so `version_preference` is inert
(deferred to 8.9). See ADR-0015.

## Access

- DI: `ICapabilityMatcher` / `CapabilityMatcher`
  (`core/bootstrap.py::_register_capability_matcher`, dormant).
- Facade: `RuntimeFacade.capability_matcher`.

## Verification

`tests/test_phase_8_step2.py` — 21 tests. Regression **734 PASS**. ADR-0015.
