"""
brain/skill_runtime/execution_persistence.py — Phase 8.10: ExecutionPersistence

Prepare step for persistence — NOT storage. Decides whether an ExecutionRecord
is acceptable for persistence and wraps it into an immutable PersistenceResult:

    ExecutionRecord → ExecutionPersistence → PersistenceResult

It does NOTHING else — never writes files/db/sqlite/json, serializes, saves,
calls memory/vector-db/telemetry/event-bus/registry/planner/workspace/network,
or mutates the record. Actual storage is a later phase. Depends only on the
ExecutionRecord + skill_runtime models.

Deterministic: ``storage_key`` is caller-supplied and never generated (no hashes,
UUIDs, timestamps); no IO.
"""

from __future__ import annotations

from brain.skill_runtime.interfaces import IExecutionPersistence
from brain.skill_runtime.models import ExecutionRecord, PersistenceResult


class ExecutionPersistence(IExecutionPersistence):
    """Deterministic, pure persistence-prepare step. Stores nothing."""

    def prepare(
        self, record: ExecutionRecord, *, storage_key: str = ""
    ) -> PersistenceResult:
        if not record.recorded:
            return PersistenceResult(persistable=False, reason="not_recorded")

        return PersistenceResult(
            persistable=True,
            record=record,
            storage_key=storage_key,
            reason="",
        )
