"""
brain/skill_creator/blueprint_verifier.py — Phase 7.3: BlueprintVerifier

Pipeline stage 02 (Verification). Consumes ONE immutable SkillBlueprint and
produces ONE immutable VerificationResult. Static checks only — evaluates the
blueprint's declared metadata against its own verification_contract. Never
mutates the blueprint, generates code, touches the filesystem, or executes
anything.

Deterministic: pure function of the blueprint. No UUID, timestamps, randomness,
hashing, filesystem, network, or LLM. Same blueprint → byte-identical
VerificationResult.

Depends only on brain.skill_creator.models, brain.skill_creator.interfaces,
typing. Implements IBlueprintVerifier.
"""

from __future__ import annotations

from typing import Dict, List

from brain.skill_creator.interfaces import IBlueprintVerifier
from brain.skill_creator.models import (
    SkillBlueprint,
    SkillPermission,
    VerificationResult,
)

# Canonical permission vocabulary (mirrors SkillPermission Literal). A blueprint
# permission outside this set fails the "permissions" check.
_ALLOWED_PERMISSIONS = frozenset(SkillPermission.__args__)

# Risk-profile keys the blueprint is expected to declare.
_RISK_KEYS = frozenset({"filesystem", "network", "shell", "workspace", "memory"})


class BlueprintVerifier(IBlueprintVerifier):
    """Deterministic static verifier for a SkillBlueprint."""

    def verify(self, blueprint: SkillBlueprint) -> VerificationResult:
        contract = blueprint.verification_contract
        checks: Dict[str, bool] = {}
        failures: List[str] = []

        # Run only the checks the blueprint's contract declares, in a stable
        # order, so the result is deterministic and contract-driven.
        for check in contract.expected_checks:
            ok, reason = self._run_check(check, blueprint)
            checks[check] = ok
            if not ok:
                failures.append(reason)

        return VerificationResult(
            blueprint_id=blueprint.id,
            recommendation_id=blueprint.recommendation_id,
            passed=not failures,
            checks=checks,
            failures=failures,
        )

    # ---- individual static checks (pure) ------------------------------

    def _run_check(self, check: str, bp: SkillBlueprint):
        if check == "schema":
            return self._check_schema(bp)
        if check == "capabilities":
            return self._check_capabilities(bp)
        if check == "permissions":
            return self._check_permissions(bp)
        if check == "risk":
            return self._check_risk(bp)
        # Unknown check declared by the contract — cannot verify it statically.
        return False, f"unknown_check:{check}"

    @staticmethod
    def _check_schema(bp: SkillBlueprint):
        if not bp.id:
            return False, "schema: blueprint id is empty"
        if not bp.recommendation_id:
            return False, "schema: recommendation_id is empty"
        if bp.blueprint_schema_version != "1.0":
            return False, f"schema: unsupported version {bp.blueprint_schema_version}"
        if bp.status != "draft":
            return False, f"schema: expected status 'draft', got '{bp.status}'"
        return True, ""

    @staticmethod
    def _check_capabilities(bp: SkillBlueprint):
        if not bp.provided_capabilities:
            return False, "capabilities: no provided_capabilities declared"
        if any(not c for c in bp.provided_capabilities):
            return False, "capabilities: empty capability entry"
        return True, ""

    @staticmethod
    def _check_permissions(bp: SkillBlueprint):
        unknown = [p for p in bp.required_permissions if p not in _ALLOWED_PERMISSIONS]
        if unknown:
            return False, f"permissions: non-canonical {sorted(unknown)}"
        return True, ""

    @staticmethod
    def _check_risk(bp: SkillBlueprint):
        missing = _RISK_KEYS - set(bp.risk_profile)
        if missing:
            return False, f"risk: missing profile keys {sorted(missing)}"
        if any(not isinstance(v, bool) for v in bp.risk_profile.values()):
            return False, "risk: profile flags must be booleans"
        return True, ""
