# Pipeline Stage 09 — Marketplace

## Purpose

Make an installed/registered skill portable — exportable to and importable from
an external skill marketplace — using only the metadata accumulated by earlier
stages. Marketplace is an OPTIONAL side branch off the registry; it never gates
the core pipeline.

## Input Artifact

One immutable `RegistryEntry` (with access to the upstream artifact chain).

## Output Artifact

One immutable `MarketplaceManifest` (future model).

## Consumes

- The `RegistryEntry` and the blueprint's `marketplace_identity`
  (exportable_identity, marketplace_tags, compatibility_family,
  semantic_version_strategy).

## Produces

- A `MarketplaceManifest` — a portable, self-describing bundle descriptor
  suitable for export. Immutable.

## Never Allowed

- Modifying any earlier artifact.
- Network calls during manifest construction (export/import transport is a
  separate, later concern).
- Executing skill code.
- Generating a non-deterministic manifest for identical input.

## Determinism Requirements

Same `RegistryEntry` + `marketplace_identity` → the same `MarketplaceManifest`.
Portable identity derives from frozen blueprint fields; no UUIDs, no inline
timestamps, no randomness.

## Future Extension Points

Export/import transport, signing, and compatibility negotiation are future
concerns that CONSUME the manifest; they never modify upstream artifacts.
