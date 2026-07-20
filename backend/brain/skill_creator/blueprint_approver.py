"""
brain/skill_creator/blueprint_approver.py — Phase 7.6: BlueprintApprover

Pipeline stage 05 (Approval) — the mandatory human gate. Consumes ONE immutable
TestResult plus an EXPLICIT human decision supplied by the caller, and produces
ONE immutable ApprovalRecord.

Rules:
  - Refuses approval when TestResult.passed is False (gated).
  - Never auto-approves and never fabricates a human decision: ``approved`` is
    True only when the caller explicitly passes approve=True AND the tests passed.
  - Generates NO timestamp — the caller supplies one if desired.

Deterministic: pure function of (test_result + supplied decision). No UUID,
datetime, randomness, hashing, filesystem, network, environment, or execution.
Same inputs -> byte-identical ApprovalRecord.

Depends only on brain.skill_creator.models, brain.skill_creator.interfaces,
typing.
"""

from __future__ import annotations

from typing import Optional

from brain.skill_creator.interfaces import IBlueprintApprover
from brain.skill_creator.models import TestResult, ApprovalRecord


class BlueprintApprover(IBlueprintApprover):
    """Deterministic human-approval gate over a TestResult."""

    def review(
        self,
        test_result: TestResult,
        *,
        approver: str,
        approve: bool,
        decision_reason: str = "",
        approval_timestamp: Optional[str] = None,
    ) -> ApprovalRecord:
        # Gate: an unpassed (or untested) package can never be approved.
        if not test_result.passed:
            return ApprovalRecord(
                blueprint_id=test_result.blueprint_id,
                recommendation_id=test_result.recommendation_id,
                approved=False,
                approver=approver,
                decision_reason=decision_reason,
                approval_timestamp=approval_timestamp,
                skipped_reason="tests_did_not_pass",
            )

        # A recorded human decision is required. approved reflects the caller's
        # explicit choice — never inferred, never defaulted to True.
        return ApprovalRecord(
            blueprint_id=test_result.blueprint_id,
            recommendation_id=test_result.recommendation_id,
            approved=bool(approve),
            approver=approver,
            decision_reason=decision_reason,
            approval_timestamp=approval_timestamp,
        )
