"""
brain/skill_runtime/skill_sandbox.py — Phase 8.4: SkillSandbox

The first runtime execution-safety layer. Given a Phase 8.3 DependencyResolution
and a SandboxPolicy, decides whether the resolved skill MAY execute — an
allow/deny verdict, nothing more.

It is PURELY a gatekeeper:
  - never loads, imports, or executes skills (loading is 8.5, execution 8.6);
  - never touches the Registry, RegistryEntry, or any skill_creator stage;
  - depends only on Phase 8.3 output (DependencyResolution) + the supplied
    SandboxPolicy.

Pure and deterministic: no I/O, network, clocks, uuids, randomness, hashing, or
mutation.

Checks, in order:
  - resolution succeeded (when policy.require_resolved) and a skill is present;
  - every permission requirement recorded by resolution is within
    policy.allowed_permissions (a granted permission outside the allowlist is a
    violation);
  - any requirement resolution already marked unsatisfied is a violation.

Risk-tier enforcement (policy.max_risk) is informational only: the frozen Phase 7
RegistryEntry projection carries no risk field, so no risk comparison is made
here (deferred; see ADR).
"""

from __future__ import annotations

from typing import List

from brain.skill_runtime.interfaces import ISkillSandbox
from brain.skill_runtime.models import (
    DependencyResolution,
    SandboxDecision,
    SandboxPolicy,
)


class SkillSandbox(ISkillSandbox):
    """Deterministic, pure runtime safety gatekeeper."""

    def evaluate(
        self, resolution: DependencyResolution, policy: SandboxPolicy
    ) -> SandboxDecision:
        violations: List[str] = []

        if policy.require_resolved and not resolution.resolved:
            return SandboxDecision(
                approved=False, skill=None,
                violations=("not_resolved",), reason="dependency resolution failed",
            )

        skill = resolution.skill
        if skill is None:
            return SandboxDecision(
                approved=False, skill=None,
                violations=("no_skill",), reason="no resolved skill to sandbox",
            )

        allowed = set(policy.allowed_permissions)

        for req in resolution.requirements:
            if req.kind == "permission" and req.value not in allowed:
                violations.append(f"permission_denied:{req.value}")
            elif not req.satisfied:
                violations.append(f"unsatisfied:{req.value or req.kind}")

        if violations:
            return SandboxDecision(
                approved=False, skill=skill,
                violations=tuple(violations),
                reason="policy violations",
            )

        return SandboxDecision(
            approved=True, skill=skill, violations=(), reason="approved",
        )
