"""
brain/skill_runtime/execution_observer.py — Phase 8.8: ExecutionObserver

Purely observational. Converts an immutable ExecutionResult into an immutable
ExecutionObservation recording descriptive metadata for later systems:

    ExecutionResult → ExecutionObserver → ExecutionObservation

It NEVER executes, retries, modifies output or memory, logs externally, touches
disk, or calls services. Depends only on the ExecutionResult + skill_runtime
models. Deterministic — the ``timestamp`` is caller-supplied and never generated
inline (a generated clock value would break reproducibility).
"""

from __future__ import annotations

from typing import Optional

from brain.skill_runtime.interfaces import IExecutionObserver
from brain.skill_runtime.models import ExecutionObservation, ExecutionResult


class ExecutionObserver(IExecutionObserver):
    """Deterministic, read-only observer of execution outcomes."""

    def observe(
        self, result: ExecutionResult, *, timestamp: Optional[str] = None
    ) -> ExecutionObservation:
        output_type = type(result.output).__name__

        if result.succeeded:
            summary = f"skill '{result.registry_key}' succeeded (output: {output_type})"
        else:
            summary = f"skill '{result.registry_key}' failed: {result.error or 'unknown'}"

        return ExecutionObservation(
            observed=True,
            registry_key=result.registry_key,
            succeeded=result.succeeded,
            error=result.error,
            output_type=output_type,
            timestamp=timestamp,
            summary=summary,
        )
