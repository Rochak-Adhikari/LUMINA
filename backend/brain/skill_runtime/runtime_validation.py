"""
brain/skill_runtime/runtime_validation.py — Phase 8.13: RuntimeValidator

Read-only structural-integrity checker. Consumes one immutable
RuntimePipelineResult and returns one immutable ValidationReport:

    RuntimePipelineResult → RuntimeValidator → ValidationReport

It asserts the result is internally consistent and does NOTHING else — never
repairs, re-runs, mutates, executes, recovers, or performs I/O. Acting on a
failed validation is out of scope (a later gated decision); this stage only
checks and reports (exactly like the Evolution Engine reports without acting).
Depends only on the RuntimePipelineResult + skill_runtime models.

Invariants asserted (deterministic, pure function of the input):

  1. contiguity   — the populated stage prefix has no gap (a stage artifact
                    never appears after a missing earlier stage).
  2. completion   — ``completed`` is True iff every stage is populated AND
                    ``reason`` is empty.
  3. reason match — a failed run's ``reason`` matches the last populated stage
                    (per the fixed stop-reason table); a completed run's
                    ``reason`` is empty.

No clocks, ids, entropy, hashing, or I/O.
"""

from __future__ import annotations

from typing import List, Tuple

from brain.skill_runtime.interfaces import IRuntimeValidator
from brain.skill_runtime.models import RuntimePipelineResult, ValidationReport

# Stage fields in pipeline order (matches RuntimePipelineResult / the 8.11
# orchestrator's call sequence).
_STAGES: Tuple[str, ...] = (
    "discovery", "match", "resolution", "sandbox", "loaded", "context",
    "execution", "observation", "record", "persistence",
)

# Failure stop-reason → last stage that must be populated when the pipeline
# stopped there. "execution_failed" is special: the orchestrator still runs the
# observer→recorder→persistence tail, so all stages are populated on that reason.
_STOP_LAST_STAGE = {
    "discovery_empty": "discovery",
    "no_match": "match",
    "unresolved": "resolution",
    "sandbox_denied": "sandbox",
    "load_failed": "loaded",
    "context_not_prepared": "context",
    "execution_failed": "persistence",
}


class RuntimeValidator(IRuntimeValidator):
    """Deterministic, read-only pipeline-result integrity checker. Repairs nothing."""

    def validate(self, result: RuntimePipelineResult) -> ValidationReport:
        populated = [name for name in _STAGES if getattr(result, name) is not None]
        present = set(populated)
        last_stage = _STAGES[max(_index(populated))] if populated else ""

        violations: List[str] = []

        # 1. Contiguity: the set of populated stages must be a gap-free prefix.
        prefix_len = len(populated)
        expected_prefix = set(_STAGES[:prefix_len])
        if present != expected_prefix:
            violations.append("noncontiguous_stages")

        # 2 + 3. Completion / reason consistency.
        all_populated = len(populated) == len(_STAGES)
        if result.completed:
            if not all_populated:
                violations.append("completed_but_incomplete")
            if result.reason:
                violations.append("completed_with_reason")
        else:
            if not result.reason:
                violations.append("failed_without_reason")
            else:
                expected_last = _STOP_LAST_STAGE.get(result.reason)
                if expected_last is None:
                    violations.append("unknown_reason")
                elif last_stage != expected_last:
                    violations.append("reason_stage_mismatch")

        checked = 3
        return ValidationReport(
            valid=not violations,
            completed=result.completed,
            checked=checked,
            last_stage=last_stage,
            violations=tuple(violations),
        )


def _index(populated: List[str]) -> List[int]:
    return [_STAGES.index(name) for name in populated]
