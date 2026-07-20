# Pipeline Stage 02 — Verification

## Purpose

Statically verify that a blueprint is well-formed and safe BEFORE any code is
generated. Verification decides whether a blueprint may proceed — it inspects
declarations (schema, capabilities, permissions, risk profile) against the
blueprint's own `verification_contract`. It is the pipeline's first gate.

## Input Artifact

One immutable `SkillBlueprint`.

## Output Artifact

One immutable `VerificationResult` (future model).

## Consumes

- The blueprint's declared fields: schema version, capabilities, permissions,
  risk_profile, `verification_contract` (expected_checks,
  required_test_categories, minimum_pass_requirements).

## Produces

- A `VerificationResult` describing which checks passed/failed and a boolean
  verdict. Descriptive only — no code, no files.

## Never Allowed

- Modifying the blueprint (or any earlier artifact).
- Generating code, writing files, or installing anything.
- Runtime execution, subprocess, network calls.
- Skipping or weakening `approval_required`.
- Emitting a non-deterministic verdict.

## Determinism Requirements

Same `SkillBlueprint` → byte-identical `VerificationResult`. Checks are static
rule evaluations over declared metadata; no randomness, timestamps, UUIDs, LLM,
or hidden state.

## Future Extension Points

New static checks may be declared via the blueprint's `verification_contract`
and produce additional fields on `VerificationResult` — a NEW model version,
never a mutation of the blueprint.
