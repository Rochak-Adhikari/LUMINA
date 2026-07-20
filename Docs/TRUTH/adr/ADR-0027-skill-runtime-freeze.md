# ADR-0027 — Skill Runtime: Phase 8 Validation & Freeze

**Status:** Accepted · Frozen
**Date:** 2026-07-20
**Amends:** ADR-0014 (Skill Runtime re-scope), ADR-0015–ADR-0026 (stages 8.1–8.13)

## Context

Phases 8.1–8.13 built the complete Skill Runtime as thirteen independent,
dormant stages in `brain/skill_runtime/` (discovery → matching → resolution →
sandbox → loader → context injection → executor → observer → recorder →
persistence → pipeline orchestrator → failure recovery → runtime validation).
Each stage shipped its own ADR, pipeline doc, and tests. The roadmap's final
Phase 8 milestone is **Validation & Freeze** — a governance gate, not a new
runtime stage. It validates the whole subsystem's invariants at once and marks
it FROZEN, exactly as Phase 6.6 and Phase 7 closed their subsystems.

## Decision

Declare the Skill Runtime **COMPLETE · VALIDATED · FROZEN**. No new runtime
behavior, models, interfaces, or facade accessors are introduced by this
milestone. A single subsystem-wide validation test asserts the invariants:

- **Contracts + DI** — all 13 runtime interfaces are registered, each resolving
  to exactly one concrete implementation, each reachable through its
  `RuntimeFacade` accessor, each a shared singleton.
- **Immutability** — every `brain/skill_runtime/models.py` model is
  `ConfigDict(frozen=True)` (≥13 models checked).
- **Boundaries (AST)** — no stage module imports `subprocess`, `threading`,
  `asyncio`, `requests`, `socket`, `sqlite3`, `core.bootstrap`, `brain.planning`,
  or `brain.skill_creator`; `importlib` appears only in the loader (its single
  sanctioned side effect).
- **Determinism** — no `datetime.now`/`utcnow`/`time.time`/`uuid`/`random`/
  `secrets` tokens in any stage module; every non-deterministic value
  (timestamp, storage_key) is caller-supplied.
- **Dormancy** — bootstrapping registers all stages without auto-invoking any;
  Phase 5 runtime behavior stays byte-identical.

## Consequences

- The Skill Runtime (8.1–8.13) is frozen: existing stages may not be renamed,
  reordered, overwritten, or redesigned (Roadmap Governance rules #2–#7). Future
  runtime work appends new phases after Phase 8.
- Phases 5–7 remain frozen and byte-identical; nothing in the runtime is wired
  into a live path. Activation is a future, explicitly-gated decision.

## Verification

`tests/test_phase_8_freeze.py` (9 subsystem checks). Full Phase 5+6+7+8
regression **913 PASS**.
