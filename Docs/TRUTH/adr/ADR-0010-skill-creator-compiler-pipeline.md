# ADR-0010 — Skill Creator Is a Compiler Pipeline (Architectural Law)

**Status:** Accepted (architectural law — binding on all Phase 7 milestones)
**Related:** ADR-0008 (Evolution Engine), ADR-0009 (reserved extension points),
ADR-0011 (SkillBlueprint schema frozen)

## Law

The Skill Creator is a **compiler pipeline**, not an AI agent. Each stage takes
an immutable input and produces an immutable output. No stage mutates or
overwrites a prior stage's output. Provenance is append-only. There is no hidden
state and no LLM in the deterministic path.

## Pipeline

```
EvolutionRecommendation   (Phase 6 — exists)
    ↓
SkillBlueprint            (Phase 7.2 — exists, frozen; stage 0)
    ↓
VerificationResult        (future — Phase 7.3)
    ↓
GenerationResult          (future)
    ↓
TestingResult             (future)
    ↓
ApprovalRecord            (future — human approval)
    ↓
InstallationRecord        (future)
    ↓
RegistryEntry             (future)
    ↓
LifecycleEvent*           (future — deprecate / retire / archive / replace)
```

## Rules (binding)

1. **Immutable input** — each stage receives frozen artifacts it never mutates.
2. **Immutable output** — each stage emits a new frozen model.
3. **No mutation** — no stage edits a previous stage's record.
4. **No overwrite** — records are append-only; history is never rewritten.
5. **Append-only provenance** — the ordered set of stage records forms a complete,
   reconstructable engineering lineage from recommendation to retirement.
6. **Deterministic transforms** — same input → byte-identical output; no UUID,
   timestamps generated inline, randomness, or hashing in the deterministic path.
7. **Explicit contracts** — every stage boundary is a declared, typed contract.
8. **Auditability + reproducibility** — every artifact is serializable and
   traceable to its origin recommendation.

## Consequence

Post-blueprint state (verification, generation, testing, approval, installation,
registry, runtime lifecycle) is modeled by that stage's OWN frozen model — never
by adding fields to an earlier stage's artifact. This is why `SkillBlueprint`
carries only pre-generation metadata and reserved contract declarations, and why
it is frozen permanently (ADR-0011).
