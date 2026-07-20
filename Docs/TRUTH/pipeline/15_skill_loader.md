# Pipeline Stage 15 — Skill Loader (Phase 8.5)

**Package:** `brain/skill_runtime/`
**Service:** `SkillLoader` (impl of `ISkillLoader`)
**Output:** `LoadedSkill` (frozen, arbitrary instance allowed)
**Status:** Dormant (DI-registered, no runtime consumer yet)

## Purpose

First stage that turns an approved skill description into a loaded, validated
instance. Import + instantiate + interface check — no execution (8.6).

## Contract

```
load(decision: SandboxDecision) -> LoadedSkill
```

## Data flow

```
SandboxDecision (stage 14)
      |
      v
SkillLoader
      |  verify approved
      |  locate <installed_location>/skill.py
      |  import module (importlib, by file path, deterministic name)
      |  instantiate Skill class
      |  validate execute/run entrypoint
      v
LoadedSkill { loaded, skill?, instance?, entrypoint, module_path, error }
```

## Errors (failure-safe, never raises)

| condition | error |
|-----------|-------|
| decision not approved | `not_approved` |
| no installed_location | `no_installed_location` |
| skill.py absent | `module_not_found` |
| import raises | `import_failed: <Type>` |
| no `Skill` class | `missing_skill_class` |
| instantiation raises | `instantiation_failed: <Type>` |
| no execute/run | `missing_entrypoint` |

## Interface contract

Installed `skill.py` exposes a `Skill` class with callable `execute` (preferred)
or `run`. Loader validates it; does **not** call it.

## Guarantees

- **8.4-only dependency** — never imports Skill Creator internals.
- Single side effect: module import from disk (importlib, no sys.path mutation,
  no eval/exec/compile/subprocess).
- Never executes, plans, caches, hot-reloads, or manages lifecycle.

## Access

- DI: `ISkillLoader` / `SkillLoader`
  (`core/bootstrap.py::_register_skill_loader`, dormant).
- Facade: `RuntimeFacade.skill_loader`.

## Verification

`tests/test_phase_8_step5.py` — 16 tests. Regression **785 PASS**. ADR-0018.
