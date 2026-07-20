# Pipeline Stage 14 — Skill Sandbox (Phase 8.4)

**Package:** `brain/skill_runtime/`
**Service:** `SkillSandbox` (impl of `ISkillSandbox`)
**Output:** `SandboxDecision` (frozen)
**Status:** Dormant (DI-registered, no runtime consumer yet)

## Purpose

First runtime execution-safety layer. Decides whether a resolved skill MAY
execute — an allow/deny verdict. Gatekeeper only: no loading (8.5), no execution
(8.6).

## Contract

```
evaluate(resolution: DependencyResolution, policy: SandboxPolicy) -> SandboxDecision
```

`SandboxPolicy`: `allowed_permissions`, `require_resolved` (default True),
`max_risk` (informational).

## Data flow

```
DependencyResolution (stage 13)  +  SandboxPolicy
      |
      v
SkillSandbox
      |  require_resolved → resolution.resolved + skill present
      |  each permission requirement ∈ allowed_permissions
      |  no unsatisfied requirement
      v
SandboxDecision { approved, skill?, violations, reason }
```

## Checks

| check | violation |
|-------|-----------|
| resolved (if `require_resolved`) | `not_resolved` |
| skill present | `no_skill` |
| permission ∈ allowlist | `permission_denied:<value>` |
| requirement satisfied | `unsatisfied:<value>` |

Approved only when `violations` is empty.

## Guarantees

- **8.3-only dependency** — never imports Registry / RegistryEntry / skill_creator.
- **Pure gatekeeper** — no load, import, or execution; no I/O, clocks, entropy,
  mutation. Deterministic.

## Deferrals

`max_risk` informational — frozen `RegistryEntry` projection has no risk field.
Execution-time permission enforcement → executor (8.6). See ADR-0017.

## Access

- DI: `ISkillSandbox` / `SkillSandbox`
  (`core/bootstrap.py::_register_skill_sandbox`, dormant).
- Facade: `RuntimeFacade.skill_sandbox`.

## Verification

`tests/test_phase_8_step4.py` — 16 tests. Regression **769 PASS**. ADR-0017.
