# Pipeline Stage 01 — Blueprint

## Purpose

Turn an approved analysis recommendation into a pre-generation architectural
drawing. This is stage 0 of the Skill Creator compiler pipeline: the first
immutable artifact that every later stage consumes. It exists so generation,
verification, and installation can all reference one stable, deterministic
description of the intended skill.

## Input Artifact

One immutable `EvolutionRecommendationSet` (Phase 6 output).

## Output Artifact

One immutable `SkillBlueprintSet` (frozen `SkillBlueprint` records).

## Consumes

- `EvolutionRecommendation` fields: id, kind, target, reason, confidence,
  related_ids.
- Deterministic builder rule tables (kind→skill_kind, DNA, complexity, family,
  risk, summary templates).

## Produces

- `SkillBlueprint` records with identity/audit, descriptive metadata, capability
  declarations, lifecycle=draft, compatibility, deterministic estimates, risk
  profile, permissions, docs/rollback/package-layout, and reserved contract
  declarations (verification/generation/installation/marketplace).

## Never Allowed

- Modifying the input recommendation set.
- Generating code, files, or packages.
- Runtime execution, filesystem, or network calls.
- Emitting any status other than "draft".
- Adding behavior/methods to the blueprint.

## Determinism Requirements

Same `EvolutionRecommendationSet` → byte-identical `SkillBlueprintSet`. Ids and
signatures are derived from input fields via fixed rule tables; no UUID, no
timestamps, no randomness, no hashing, no LLM. Insertion order preserved.

## Future Extension Points

New reserved contract declarations may be added by later stages as their OWN
models — never as new blueprint fields (ADR-0011: schema frozen). The blueprint
is permanently frozen; extension happens downstream.
