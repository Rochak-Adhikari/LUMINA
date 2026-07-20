# ADR-0011 — SkillBlueprint Schema Frozen

**Status:** Accepted (schema freeze — permanent)
**Related:** ADR-0009 (reserved extension points), ADR-0010 (compiler-pipeline law)

## Decision

As of Phase 7.2.6, the `SkillBlueprint` schema is **FROZEN PERMANENTLY**. It will
not be modified again. All future Skill Creator work (verification, generation,
testing, approval, installation, registry, marketplace, rollback, evolution)
consumes the blueprint exactly as it exists and produces its own NEW immutable
stage models.

No future schema migrations. No breaking changes. Only new immutable stage
outputs.

## What the frozen blueprint contains

`SkillBlueprint` is a stage-0, PRE-GENERATION architectural drawing. It holds:

- **Identity + audit**: `id`, `recommendation_id` (mandatory), `canonical_signature`,
  `blueprint_schema_version`.
- **Descriptive metadata**: name, description, purpose, `skill_kind`,
  `skill_family`, `semantic_fingerprint`, `human_summary`, `skill_dna`,
  `source_recommendation_ids`.
- **Capabilities**: `provided_capabilities`, `required_capabilities`.
- **Lifecycle + safety**: `status` (draft), `approval_required=True`.
- **Compatibility**: `minimum_runtime_version`, `minimum_api_version`.
- **Deterministic estimates**: complexity, tokens, files, test_count, generation
  tokens/steps.
- **Structured risk + permissions**: `risk_profile`, canonical `required_permissions`.
- **Docs + rollback + package layout**: `documentation`, `include_changelog`,
  `rollback_strategy`, frozen `package_layout`.
- **Reserved contract declarations** (metadata only, no behavior):
  `expected_quality_dimensions`, `verification_contract`, `generation_contract`,
  `installation_contract`, `marketplace_identity`.

## What must NEVER be added to the blueprint

Anything representing a LATER pipeline stage's result or runtime state:
quality scores, generated code, validation/test results, approval records,
installation records, registry entries, runtime lifecycle beyond draft. These
belong to their own future frozen models (ADR-0010).

## Guarantees

- Frozen (`ConfigDict(frozen=True)`), serializable, deterministic.
- No methods, no behavior, no executable payload, no runtime imports.
- Reserved contracts let later phases attach richer declarations WITHOUT schema
  change — they populate existing typed fields or emit new stage models.

## Why no future migration is required

Every foreseeable future concept is either (a) already a typed field / reserved
contract on the blueprint, or (b) a post-blueprint stage that gets its own model.
Because the compiler-pipeline law (ADR-0010) forbids folding later-stage state
into earlier artifacts, the blueprint has no reason to change again.
