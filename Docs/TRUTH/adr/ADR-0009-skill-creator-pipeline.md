# ADR-0009 — Skill Creator Pipeline: Reserved Extension Points

**Status:** Accepted (Phase 7.2.5 — reservation only, no implementation)
**Related:** ADR-0008 (Evolution Engine), `Docs/TRUTH/ENGINEERING_ROADMAP.md`
(Phase 7 — Skill Creator), `brain/skill_creator/`

## Purpose

Reserve future Skill Creator architectural concepts NOW so later Phase 7
milestones (verification, generation, testing, installation, registry, rollback)
can be added WITHOUT breaking changes or schema migrations. This ADR records
contracts and extension points only. Nothing here is implemented; runtime stays
byte-identical.

## Engineering Philosophy (binding)

The Skill Creator is built like a **compiler pipeline**, not an AI agent. Every
stage MUST have: immutable inputs, immutable outputs, deterministic transforms,
explicit contracts, auditability, reproducibility. No hidden mutations, no
magical state, no LLM in the deterministic path.

Consequence: each pipeline stage owns its OWN frozen output model. Post-blueprint
state (generated code, validation, testing, approval, install, registry,
lifecycle beyond draft) is NEVER modeled as fields on `SkillBlueprint` — the
blueprint is the pre-generation drawing and must stay immutable and stage-0.

## Pipeline Stages (each a future frozen model, one direction only)

```
EvolutionRecommendation  (Phase 6, exists)
   → SkillBlueprint       (Phase 7.2, exists — stage 0, frozen)
   → GeneratedSkill        (future — code artifact metadata)
   → ValidationResult      (future)
   → TestResult            (future)
   → ApprovalRecord        (future — human approval; ADR-0008 gate)
   → InstallationRecord    (future)
   → RegistryEntry         (future)
   → LifecycleEvent*       (future — deprecate / retire / archive / replace)
```

Each stage appends an immutable record; no stage overwrites a prior stage. The
concatenation forms the **complete provenance chain** — a full engineering
lineage from origin recommendation to retirement.

## Reserved Concepts

1. **Skill Quality Score** — post-generation/validation/testing. A future frozen
   model (architecture/readability/maintainability/performance/determinism/
   safety/documentation/testing/overall). Deterministic + reproducible. NOT a
   blueprint field; attaches to `GeneratedSkill`/`TestResult` stage.
2. **Semantic Fingerprint** — seeded on the blueprint NOW
   (`SkillBlueprint.semantic_fingerprint`, e.g. `workspace.memory.<target>.v1`).
   Semantic identity, NOT a hash/checksum/UUID. Later used for duplicate/similar
   detection and semantic search.
3. **Complete Provenance Chain** — the append-only stage records above. Each
   stage immutable; lineage reconstructable end to end.
4. **Skill Evolution History** — future metadata on later stages: generated_from
   recommendation id, blueprint/generator/validator/installer versions, creation
   date (supplied, never inline-generated), superseded_by, deprecated_by,
   retired_by.
5. **Duplicate Prevention** — future, uses semantic_fingerprint + skill_dna +
   capabilities + quality score. Blueprint already carries the first three; no
   architecture blocks it.
6. **Skill Family** — seeded on the blueprint NOW (`SkillBlueprint.skill_family`,
   e.g. `workspace.memory`). Registry may group siblings later.
7. **Extended Lifecycle** — the blueprint lifecycle Literal stays draft-oriented.
   Runtime lifecycle beyond installed (active/deprecated/retired/archived/
   replaced) belongs to `LifecycleEvent` records, not the blueprint. Reserved,
   not added to the blueprint enum, to avoid modeling runtime state on a
   pre-generation artifact.
8. **Skill Marketplace** — future export/import. Portability comes from the
   accumulated frozen stage records (blueprint + provenance + metadata); no
   packager/importer/exporter now.

## What Was Added in Phase 7.2.5 (seed fields only)

- `SkillBlueprint.semantic_fingerprint` — deterministic `<family>.<target>.v1`.
- `SkillBlueprint.skill_family` — deterministic sibling grouping.

Both are metadata only, deterministic, frozen, serializable. All other reserved
concepts remain future frozen models owned by their own stage — deliberately NOT
blueprint fields.

## Decision

The blueprint schema is mature for Phase 7.3. Do not overload `SkillBlueprint`
with post-generation state. Each later stage introduces its own immutable model
consuming the previous stage's output — preserving the compiler-pipeline
guarantees above.
