# Pipeline Stage 04 — Testing

## Purpose

Execute the generated skill's tests in isolation and record the outcome. Testing
proves the generated artifact behaves as its blueprint declared, before a human
is asked to approve it.

## Input Artifact

One immutable `GenerationResult` (which references its blueprint + verification).

## Output Artifact

One immutable `TestResult` (future model).

## Consumes

- The generated package's declared tests and the blueprint's
  `required_test_categories` / `minimum_pass_requirements`.

## Produces

- A `TestResult` recording per-category pass/fail counts and a boolean verdict.
  Descriptive only.

## Never Allowed

- Modifying the generation result, blueprint, or verification result.
- Installing, activating, or registering the skill.
- Running generated code OUTSIDE an isolated sandbox.
- Approving on the skill's behalf.
- Non-deterministic verdicts for identical input + environment.

## Determinism Requirements

Same `GenerationResult` under the same pinned test environment → the same
`TestResult`. Test selection and aggregation are deterministic; the record must
capture enough environment identity to be reproducible. No inline timestamps or
UUIDs in the artifact (any timing captured is supplied, not generated in the
deterministic path).

## Future Extension Points

New test categories declared via the blueprint's contract; recorded on
`TestResult`.
