# Pipeline Stage 05 — Approval

## Purpose

Require an explicit human decision before a tested skill may be installed. This
is the mandatory approval gate (ADR-0008). Nothing downstream may run without a
recorded human approval.

## Input Artifact

One immutable `TestResult` (which references generation → verification → blueprint).

## Output Artifact

One immutable `ApprovalRecord` (future model).

## Consumes

- The `TestResult` verdict, the blueprint's `approval_required` flag (always
  True), risk_profile, and human-supplied approval metadata (approver identity,
  note, decision).

## Produces

- An `ApprovalRecord` capturing approver identity, decision (approved/rejected),
  and note. Immutable once written.

## Never Allowed

- Modifying any earlier artifact.
- Auto-approving, or bypassing/weakening the gate.
- Installing or registering the skill.
- Executing code.
- Inferring approval from analysis (approval is human-only).

## Determinism Requirements

The record deterministically reflects the human decision + input artifacts. The
approval DECISION is external human input (not computed); the ARTIFACT that
records it is deterministic and reproducible from (TestResult + supplied approval
metadata). No UUIDs/timestamps generated inline — supplied if needed.

## Future Extension Points

Multi-party or policy-scoped approval recorded as additional `ApprovalRecord`
fields; the gate itself can never be removed (ADR-0008).
