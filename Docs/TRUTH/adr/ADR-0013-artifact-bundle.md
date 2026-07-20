# ADR-0013 — SkillArtifactBundle (Reserved Concept)

**Status:** Reserved (architecture only — no implementation)
**Related:** ADR-0010 (compiler pipeline), ADR-0012 (artifact immutability),
`Docs/TRUTH/pipeline/`

## Reservation

Reserve the future concept `SkillArtifactBundle`: an aggregate that will
eventually collect, in order, every immutable artifact produced for one skill
across the pipeline:

```
SkillArtifactBundle (future — reserved, NOT implemented)
  ├─ SkillBlueprint          (stage 01 — exists)
  ├─ VerificationResult      (stage 02 — future)
  ├─ GenerationResult        (stage 03 — future)
  ├─ TestResult              (stage 04 — future)
  ├─ ApprovalRecord          (stage 05 — future)
  ├─ InstallationRecord      (stage 06 — future)
  ├─ RegistryEntry           (stage 07 — future)
  ├─ LifecycleEvent[]        (stage 08 — future, append-only)
  ├─ RollbackRecord          (stage 10 — future, optional)
  └─ MarketplaceManifest     (stage 09 — future, optional)
```

## Purpose (future)

- Provide the complete engineering lineage for one skill as a single portable,
  serializable object.
- Serve as the export/import unit for the marketplace (stage 09).
- Give auditors one handle to the full provenance chain.

## Rules (when implemented)

- The bundle AGGREGATES existing immutable artifacts; it never mutates or
  replaces them (ADR-0012).
- It is itself frozen and serializable; adding a stage artifact yields a NEW
  bundle value, never an in-place edit.
- It carries no behavior and no executable payload.

## Status in Phase 7.2.7

Reserved only. No implementation, no code, no model, no runtime, no imports.
This ADR exists so later phases can introduce `SkillArtifactBundle` as a NEW
frozen model without any schema migration or architectural redesign.
