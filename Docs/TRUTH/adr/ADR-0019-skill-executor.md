# ADR-0019 — Skill Runtime: Skill Executor + Canonical run() (Phase 8.6)

**Status:** Accepted · Dormant
**Date:** 2026-07-20
**Amends:** ADR-0018 (Skill Loader)

## Context

After loading (8.5), the runtime must actually run a skill. Phase 8.6 is the
first stage that executes skill code end-to-end. It also standardizes the
runtime execution interface.

## Decision

### 1. Canonical entrypoint: `run(context)`

The runtime has ONE canonical execution interface going forward: `run(context)`.
A skill exposing only a legacy `execute` is bridged by a **minimal shim** (loader
reports the canonical `"run"` entrypoint; executor falls back to `execute` when
`run` is absent). No permanent dual interface. (Phase 7's generated scaffold
already emits `run`.) This narrows the earlier "execute or run" acceptance to a
single canonical name plus a documented compatibility fallback.

### 2. `SkillExecutor` (impl of `ISkillExecutor`)

- **Input:** Phase 8.5 `LoadedSkill` (+ optional `context`).
  **Output:** immutable `ExecutionResult`.
- Does exactly one thing: validate loaded → call `run(context)` **once** →
  capture → return. Never retries, recovers, chains, plans, loads, sandboxes,
  injects memory, or schedules.
- **Never propagates exceptions** — unloaded skill, missing interface, or a skill
  raising all become a structured `ExecutionResult` (`not_loaded`,
  `no_entrypoint`, `execution_failed: <Type>`). Depends only on 8.5 output.

`ExecutionResult` is a frozen model with `arbitrary_types_allowed=True` to carry
the skill's return value; not serialized to disk.

## Consequences

- Pipeline complete end-to-end: discovery → matching → resolution → sandbox →
  loader → **executor**. A loaded skill can now be run.
- Phase 5–7 untouched, byte-identical; executor dormant in DI +
  `RuntimeFacade.skill_executor`.
- Deferred to later phases (unchanged): context injection (8.7), failure recovery
  /retry (8.8), version resolution (8.9), chaining (8.10).

## Verification

`tests/test_phase_8_step6.py` (17 tests) + updated `test_phase_8_step5.py`
(canonical entrypoint). Full regression **802 PASS**.
