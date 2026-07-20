# ADR-0018 — Skill Runtime: Skill Loader (Phase 8.5)

**Status:** Accepted · Dormant
**Date:** 2026-07-20
**Amends:** ADR-0017 (Skill Sandbox)

## Context

After the sandbox (8.4) approves a resolved skill, the runtime needs a usable
instance before it can execute (8.6). Phase 8.5 is the first stage that
materializes a real object from an installed skill package.

## Decision

Add `SkillLoader` (impl of `ISkillLoader`) to `brain/skill_runtime/`.

- **Input:** Phase 8.4 `SandboxDecision`. **Output:** immutable `LoadedSkill`.
- Does exactly one thing: verify approval → locate `<installed_location>/skill.py`
  → import module (by file path) → instantiate `Skill` → validate an
  `execute`/`run` entrypoint → return `LoadedSkill`.
- **Never executes** the skill (that is 8.6), calls tools, plans, schedules,
  caches, hot-reloads, or manages lifecycle. Depends only on 8.4 output; never
  imports Skill Creator internals.

### Interface contract with generated packages

The installed implementation file is `skill.py`, exposing a `Skill` class with a
callable `execute` (preferred) or `run`. Phase 7 currently emits an inert `run`
scaffold; the loader validates the interface, it does **not** call it.

### Side effects & safety

Loading imports a module from disk — the single permitted side effect at this
stage. Import is by `importlib.util.spec_from_file_location` (no `sys.path`
mutation, no package assumptions), under a deterministic module name derived from
the registry key. Everything is failure-safe: any locate/import/instantiate/
validate error yields `loaded=False` with a descriptive `error`; the loader
never raises out. No `eval`/`exec`/`compile`/`subprocess`.

`LoadedSkill` is a frozen model with `arbitrary_types_allowed=True` to carry the
live instance; it is not serialized to disk.

## Consequences

- Pipeline: … sandbox → **loader** → (execute, 8.6).
- Phase 5–7 untouched, byte-identical; loader dormant in DI +
  `RuntimeFacade.skill_loader`.
- 8.6 (Executor) consumes a `LoadedSkill` and calls its recorded entrypoint.

## Verification

`tests/test_phase_8_step5.py` (16 tests). Full regression **785 PASS**.
