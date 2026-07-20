# Pipeline Stage 13 — Dependency Resolution (Phase 8.3)

**Package:** `brain/skill_runtime/`
**Service:** `DependencyResolver` (impl of `IDependencyResolver`)
**Output:** `DependencyResolution` (frozen)
**Status:** Dormant (DI-registered, no runtime consumer yet)

## Purpose

The gate between matching (stage 12) and loading (stage 14, future). Confirms the
chosen candidate is ready — registered, installed, capability-permitted, running
under acceptable grants — before anything loads or executes.

## Contract

```
resolve(matches: CapabilityMatchResult, *,
        granted_permissions=(), runtime_version="",
        available_capabilities=None) -> DependencyResolution
```

## Data flow

```
CapabilityMatchResult (stage 12)  +  runtime grants
      |
      v
DependencyResolver
      |  for each match in ranked order:
      |    check requirements (registration, install, capability, runtime, permission)
      |    first fully-satisfied wins
      v
DependencyResolution { resolved, skill?, requirements[], unsatisfied, reason }
```

## Requirements

| kind | rule |
|------|------|
| registration | `registration_status == "registered"` |
| install | `installed_location` non-empty |
| capability | `skill_family ∈ available_capabilities` (when supplied) |
| runtime | supplied `runtime_version` recorded satisfied (deferred to 8.9) |
| permission | each granted permission recorded (enforcement deferred to 8.4) |

## Guarantees

- **8.2-only dependency** — never imports Registry / RegistryEntry / skill_creator.
- **Pure + deterministic** — no I/O, clocks, entropy, loading, or execution;
  first satisfied candidate in the deterministic match order wins.
- **Read-only** — no mutation of matches or discovery results.

## Deferrals

Permission enforcement → Sandbox (8.4); version constraints → Version Resolution
(8.9). The frozen `RegistryEntry` projection exposes no required_permissions or
minimum_version. See ADR-0016.

## Access

- DI: `IDependencyResolver` / `DependencyResolver`
  (`core/bootstrap.py::_register_dependency_resolver`, dormant).
- Facade: `RuntimeFacade.dependency_resolver`.

## Verification

`tests/test_phase_8_step3.py` — 19 tests. Regression **753 PASS**. ADR-0016.
