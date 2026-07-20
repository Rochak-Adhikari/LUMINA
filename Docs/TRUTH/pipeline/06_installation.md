# Pipeline Stage 06 — Installation

## Purpose

Place an approved, tested skill into its runtime location and prepare it for
registry entry. Installation is the first stage that changes on-disk state — and
it may only proceed from a recorded human approval.

## Input Artifact

One immutable `ApprovalRecord` (which references test → generation → verification
→ blueprint).

## Output Artifact

One immutable `InstallationRecord` (future model).

## Consumes

- The `ApprovalRecord` (must be approved), the blueprint's
  `installation_contract` (install_targets, rollback_targets,
  activation_strategy, dependency_strategy), and the generated package.

## Produces

- An `InstallationRecord` capturing installed paths, activation strategy applied,
  and rollback targets. Immutable.

## Never Allowed

- Modifying any earlier artifact.
- Installing without an approved `ApprovalRecord`.
- Activating a skill whose `activation_strategy` is manual without explicit action.
- Executing arbitrary generated code during install.
- Non-deterministic install layout for identical input.

## Determinism Requirements

Same `ApprovalRecord` + package + declared install targets → the same installed
layout and `InstallationRecord`. Target paths come from the blueprint's
`installation_contract`, not computed randomly. Filesystem side effects are
permitted here (unlike earlier stages) but must be idempotent and reproducible.

## Future Extension Points

Dependency resolution strategies declared via `installation_contract`; recorded
on `InstallationRecord`. Rollback consumes this record (stage 10).
