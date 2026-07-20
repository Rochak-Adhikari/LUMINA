# Pipeline Stage 10 — Rollback

## Purpose

Undo an installation using only the immutable records captured during install.
Rollback restores the pre-installation state; it does not delete or rewrite the
provenance chain — the rollback itself is recorded as a new immutable artifact.

## Input Artifact

One immutable `InstallationRecord` (and the blueprint's `rollback_strategy` /
`installation_contract.rollback_targets`).

## Output Artifact

One immutable `RollbackRecord` (future model).

## Consumes

- The `InstallationRecord` (installed paths, rollback targets) and the blueprint's
  declared `rollback_strategy` (default "remove_generated_skill").

## Produces

- A `RollbackRecord` capturing what was removed/reverted and the resulting state.
  Append-only. A subsequent `LifecycleEvent` (retired/replaced) may reference it.

## Never Allowed

- Modifying or deleting any earlier artifact (including the InstallationRecord).
- Rolling back without an `InstallationRecord` to drive it.
- Executing skill code during rollback.
- Rewriting provenance (rollback is additive — a new record, not an erasure).
- Non-deterministic rollback for identical input.

## Determinism Requirements

Same `InstallationRecord` + declared `rollback_strategy` → the same reverted
state and `RollbackRecord`. Targets come from recorded install metadata, not
recomputed. Filesystem effects must be idempotent and reproducible.

## Future Extension Points

Alternate rollback strategies declared via the blueprint's fields; recorded on
`RollbackRecord`. Partial/staged rollback is additive, never a mutation of prior
records.
