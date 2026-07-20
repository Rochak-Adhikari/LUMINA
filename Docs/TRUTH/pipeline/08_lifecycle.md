# Pipeline Stage 08 — Lifecycle

## Purpose

Record runtime lifecycle transitions of a registered skill (active → deprecated
→ retired → archived → replaced) as append-only events. Lifecycle state lives
here, NOT on the blueprint (which is permanently draft-oriented, ADR-0011).

## Input Artifact

One immutable `RegistryEntry` (plus the specific transition being requested).

## Output Artifact

One immutable `LifecycleEvent` (future model). Each transition = one new event.

## Consumes

- The `RegistryEntry`, the prior `LifecycleEvent` history (read-only), and a
  supplied transition intent (e.g. deprecate, retire, replace-by).

## Produces

- A `LifecycleEvent` recording the from-state, to-state, and references
  (superseded_by / deprecated_by / retired_by). Append-only.

## Never Allowed

- Modifying the registry entry or any prior lifecycle event.
- Rewriting lifecycle history (append-only).
- Skipping states illegally (transitions follow the declared lifecycle order).
- Executing skill code.
- Non-deterministic event content for identical input.

## Determinism Requirements

Same `RegistryEntry` + prior events + supplied transition → the same
`LifecycleEvent`. The transition target is supplied input; the event artifact is
deterministic and reproducible. No inline timestamps/UUIDs (supplied if needed).

## Future Extension Points

Extended lifecycle states (archived, replaced) are new `LifecycleEvent` to-state
values — additive, never a blueprint or registry mutation.
