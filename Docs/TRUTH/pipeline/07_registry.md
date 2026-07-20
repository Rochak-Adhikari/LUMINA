# Pipeline Stage 07 — Registry

## Purpose

Record an installed skill in the skill registry so the runtime can discover it.
The registry is the catalog of installed skills and their identities/families;
it makes an installed skill referable without exposing pipeline internals.

## Input Artifact

One immutable `InstallationRecord` (references the full upstream chain).

## Output Artifact

One immutable `RegistryEntry` (future model).

## Consumes

- The `InstallationRecord`, and the blueprint's identity fields
  (`semantic_fingerprint`, `skill_family`, `provided_capabilities`,
  `marketplace_identity`).

## Produces

- A `RegistryEntry` binding the skill's semantic identity, family, capabilities,
  and installed location. Append-only in the registry.

## Never Allowed

- Modifying any earlier artifact.
- Registering a skill without an `InstallationRecord`.
- Overwriting an existing registry entry (append-only; supersession is a new
  entry + lifecycle event).
- Executing skill code.
- Non-deterministic entry content for identical input.

## Determinism Requirements

Same `InstallationRecord` + blueprint identity → the same `RegistryEntry`
content. Identity/family come from frozen blueprint fields. No UUIDs; the entry
key derives from `semantic_fingerprint`.

## Future Extension Points

Family grouping, duplicate detection, and semantic search read `RegistryEntry` +
`semantic_fingerprint` + `skill_dna`; all additive, never a blueprint change.
