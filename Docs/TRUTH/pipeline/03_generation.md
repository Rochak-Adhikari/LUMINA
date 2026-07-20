# Pipeline Stage 03 — Generation

## Purpose

Produce the skill package artifacts (code, manifest, tests, metadata, readme,
provenance) from a verified blueprint. Generation is the first stage that emits
a code artifact — but as immutable metadata describing generated content, not by
executing anything.

## Input Artifact

One immutable `VerificationResult` (which references its verified `SkillBlueprint`).

## Output Artifact

One immutable `GenerationResult` (future model) describing the generated package.

## Consumes

- The verified blueprint's `generation_contract` (expected_output_packages,
  expected_module_layout, expected_manifest_version, expected_registry_entries),
  `package_layout`, capabilities, and estimates.
- The `VerificationResult` verdict (must be passing to proceed).

## Produces

- A `GenerationResult` recording the generated package layout, manifest version,
  and content descriptors. Whether files are written to a staging area is an
  installation concern — generation records WHAT was produced.

## Never Allowed

- Modifying the blueprint or verification result.
- Installing, activating, or registering anything.
- Executing generated code.
- Bypassing a failed verification.
- Non-deterministic output for identical input.

## Determinism Requirements

Same `VerificationResult` (and its blueprint) → byte-identical `GenerationResult`.
Generation is a deterministic transform driven by the blueprint's declared
layout/contract; no randomness, timestamps, UUIDs, or LLM variability in the
deterministic path. (Any future model-assisted generation must be pinned and
recorded so the artifact remains reproducible.)

## Future Extension Points

Additional output package kinds or manifest versions declared via
`generation_contract`; recorded on `GenerationResult`, never on the blueprint.
