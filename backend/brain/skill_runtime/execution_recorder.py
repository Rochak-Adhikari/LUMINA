"""
brain/skill_runtime/execution_recorder.py — Phase 8.9: ExecutionRecorder

Pure transformation. Converts one immutable ExecutionObservation into one
immutable ExecutionRecord, ready for later persistence:

    ExecutionObservation → ExecutionRecorder → ExecutionRecord

It does NOT persist, log, save, learn, update memory, execute, retry, reload, or
mutate the observation. Persistence is a future phase — this stage only prepares
the record. Depends only on the ExecutionObservation + skill_runtime models.

Deterministic: ``metadata`` is copied (never aliased), ``timestamp`` is
caller-supplied and never generated, no clocks/randomness/IO.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional

from brain.skill_runtime.interfaces import IExecutionRecorder
from brain.skill_runtime.models import ExecutionObservation, ExecutionRecord


class ExecutionRecorder(IExecutionRecorder):
    """Deterministic, pure observation→record transformer. No persistence."""

    def record(
        self,
        observation: ExecutionObservation,
        *,
        conversation_id: str = "",
        metadata: Optional[dict] = None,
        timestamp: Optional[str] = None,
    ) -> ExecutionRecord:
        if not observation.observed:
            return ExecutionRecord(recorded=False, reason="not_observed")

        return ExecutionRecord(
            recorded=True,
            registry_key=observation.registry_key,
            conversation_id=conversation_id,
            summary=observation.summary,
            succeeded=observation.succeeded,
            output_type=observation.output_type,
            error=observation.error,
            metadata=self._copy(metadata),
            timestamp=timestamp,
            reason="recorded",
        )

    @staticmethod
    def _copy(value: Optional[dict]) -> Dict[str, Any]:
        # Deep copy so nested caller data is never aliased into the frozen record;
        # inputs are never mutated.
        return copy.deepcopy(value) if value else {}
