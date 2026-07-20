"""
brain/skill_runtime/failure_recovery.py — Phase 8.12: FailureRecovery

Descriptive recovery advisor. Consumes one immutable RuntimePipelineResult and
returns one immutable RecoveryPlan:

    RuntimePipelineResult → FailureRecovery → RecoveryPlan

It names WHAT recovery should happen for a failed run. It does NOTHING else —
never retries, re-invokes the pipeline, executes, loads, loops, branches into
orchestration, plans, writes memory, or mutates the result. Acting on a plan is
a future gated phase; this stage only produces advice (exactly like the
Evolution Engine decides WHAT without performing it). Depends only on the
RuntimePipelineResult + skill_runtime models.

Deterministic: a pure function of the input ``reason`` — a fixed reason→strategy
table, no clocks, ids, entropy, hashing, or I/O.
"""

from __future__ import annotations

from typing import Tuple

from brain.skill_runtime.interfaces import IFailureRecovery
from brain.skill_runtime.models import RecoveryPlan, RuntimePipelineResult

# Fixed, deterministic advisory table: pipeline stop-reason -> (strategy,
# retryable, rationale). Descriptive only — no reason maps to an action that
# executes anything. Transient failures (a fresh run could plausibly differ) are
# retryable; structural failures are not.
_PLAYBOOK = {
    "discovery_empty": (
        "review_required", False,
        "no skill discovered for the query; nothing to recover automatically",
    ),
    "no_match": (
        "rematch_capability", False,
        "no skill satisfied the capability request; broaden or revise the request",
    ),
    "unresolved": (
        "review_required", False,
        "dependencies/grants unsatisfied; adjust permissions or runtime version",
    ),
    "sandbox_denied": (
        "abort", False,
        "sandbox policy denied execution; a safety decision, not recoverable here",
    ),
    "load_failed": (
        "retry_transient", True,
        "skill module failed to load; a transient import/instantiation fault may clear",
    ),
    "context_not_prepared": (
        "review_required", False,
        "execution context could not be built; inspect the loaded skill inputs",
    ),
    "execution_failed": (
        "retry_transient", True,
        "skill raised during execution; a transient runtime fault may clear on retry",
    ),
}

_NONE: Tuple[str, bool, str] = ("none", False, "")


class FailureRecovery(IFailureRecovery):
    """Deterministic, descriptive recovery advisor. Acts on nothing."""

    def plan(self, result: RuntimePipelineResult) -> RecoveryPlan:
        if result.completed:
            return RecoveryPlan(
                needed=False, completed=True, registry_key=result.registry_key,
                strategy="none", retryable=False,
                rationale="pipeline completed; no recovery needed",
            )

        strategy, retryable, rationale = _PLAYBOOK.get(result.reason, _NONE)
        return RecoveryPlan(
            needed=True,
            completed=False,
            failed_stage=result.reason,
            registry_key=result.registry_key,
            strategy=strategy,
            retryable=retryable,
            rationale=rationale,
        )
