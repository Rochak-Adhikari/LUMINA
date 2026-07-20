# ADR-0020 — Skill Runtime: Context Injection (Phase 8.7)

**Status:** Accepted · Dormant
**Date:** 2026-07-20
**Amends:** ADR-0019 (Skill Executor)

## Context

The executor calls `run(context)`, but `context` was still raw. Phase 8.7 adds
the stage that PREPARES everything a skill needs before execution, as immutable
data.

## Decision

Add `ContextInjector` (impl of `IContextInjector`) to `brain/skill_runtime/`.

- **Input:** Phase 8.5 `LoadedSkill` + caller-supplied data.
  **Output:** immutable `ContextInjectionResult` wrapping a frozen
  `ExecutionContext`.
- Pure transformation: never loads, executes, retries, recovers, chains,
  schedules, accesses the registry, imports skill_creator, plans, writes memory,
  or runs tools/network/subprocess.
- **Inputs never mutated** — supplied snapshot/variable/metadata dicts are copied
  into the frozen context (plain read-only data; no live services, no runtime
  objects, no raw skill instance).

### `ExecutionContext` fields

`registry_key`, `conversation_id`, `user_input`, `memory_snapshot`,
`workspace_snapshot`, `environment_snapshot`, `available_tools`, `variables`,
`metadata` — all frozen primitives/dicts/tuples.

### Refinement note (Phase 8.6 verified)

Confirmed before implementing 8.7: canonical entrypoint is `run(context)`
(legacy `execute` shim confined to loader/executor); `LoadedSkill.instance` is
accessed only by loader (sets) and executor (reads). The injector does **not**
read the raw instance — only the skill's `registry_key` crosses into the
context. No adjustment needed.

## Consequences

- Pipeline: … loader → **context injection** → executor. The executor will
  receive a prepared `ExecutionContext` once wiring is enabled.
- Phase 5–7 untouched, byte-identical; injector dormant in DI +
  `RuntimeFacade.context_injector`.
- Deferred (unchanged): failure recovery (8.8), version resolution (8.9),
  chaining (8.10).

## Verification

`tests/test_phase_8_step7.py` (15 tests). Full regression **817 PASS**.
