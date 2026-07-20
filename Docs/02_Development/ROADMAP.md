# Lumina Development Roadmap

> **Superseded.** The authoritative engineering roadmap now lives at
> `Docs/TRUTH/ENGINEERING_ROADMAP.md` (frozen, governed). The long-term product
> vision lives at `Docs/TRUTH/ROADMAP.md`. This file is retained only as a
> pointer to avoid duplication/drift.

## Current State (summary)

- **Phases 1–4** — Runtime foundation, state migration, architectural migration,
  stable runtime recovery. **Complete / frozen.**
- **Phase 5 — Cognitive Architecture** — BrainCore, Planning & Skills, Capability
  Layer, Workspace Memory, Reflection Engine, Workspace Activation, Workspace
  Reasoning (retrieval → planning → prompting). **Complete / frozen.**
- **Phase 6 — Evolution Engine** — analysis-only, dormant: Reflection Learning,
  Strategy Improvement, Performance Analysis, Memory Consolidation, Self
  Evolution (Recommendation Engine), Validation & Freeze. **Complete · validated
  · frozen.**
- **Phase 7 — Skill Creator** — deterministic 10-stage compiler pipeline
  (Builder→Verifier→Generator→Tester→Approver→Installer→Registry→Lifecycle→
  Marketplace→Rollback), all stages dormant in DI. **Complete · validated ·
  frozen.**

## Next

- **Phase 8 — Skill Runtime** — the runtime that USES created skills: consumes
  `RegistryEntry` and runtime requests to discover, validate, sandbox, load, and
  execute installed skills. Not started.
- **Autonomous Planning** — long-horizon goals, multi-step execution,
  self-scheduling. Not started.

For how each shipped feature works, see `Docs/04_Guides/FEATURE_GUIDE.md`.
For architecture decisions, see `Docs/TRUTH/adr/`.
