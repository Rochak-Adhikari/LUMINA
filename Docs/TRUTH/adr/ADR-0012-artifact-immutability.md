# ADR-0012 — Artifact Immutability (Architectural Law)

**Status:** Accepted (permanent architectural law)
**Related:** ADR-0010 (compiler-pipeline law), ADR-0011 (blueprint frozen),
`Docs/TRUTH/pipeline/`

## Law

**No pipeline stage may modify an artifact produced by an earlier stage.**

Every Skill Creator stage may only:

- **consume** earlier immutable artifacts (read-only),
- **validate** them,
- **transform** their information, and
- **produce a NEW immutable artifact**.

A stage may NEVER:

- mutate an earlier artifact,
- overwrite an earlier artifact,
- recycle/reuse an artifact instance as its own output.

## Rationale

The Skill Creator is a compiler (ADR-0010). Immutable artifacts give:

- **Auditability** — the full chain from `EvolutionRecommendation` →
  `SkillBlueprint` → ... → `LifecycleEvent` is reconstructable and never rewritten.
- **Reproducibility** — deterministic transforms over immutable inputs yield
  byte-identical outputs.
- **Safety** — no stage can silently corrupt an upstream decision (e.g.
  generation cannot alter a verification verdict; installation cannot alter an
  approval).

## Consequences

- Each stage owns exactly one frozen output model.
- Provenance is append-only: new records are added, never edited.
- "Supersession" (a newer skill replacing an older one) is a NEW artifact +
  `LifecycleEvent`, not an in-place edit.
- All artifacts are frozen pydantic models: deterministic, serializable, no
  behavior, no executable payload.

## Enforcement

Every stage spec in `Docs/TRUTH/pipeline/*` lists "modifying previous artifacts"
under **Never Allowed**. Future stage implementations must accept frozen inputs
and return new frozen outputs; tests must assert inputs are unchanged.
