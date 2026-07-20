"""
brain/skill_runtime/skill_executor.py — Phase 8.6: SkillExecutor

Runs a loaded skill exactly once. The first stage that actually executes skill
code. It does EXACTLY one thing:

    LoadedSkill → validate loaded → call run(context) once → capture → ExecutionResult

It NEVER retries, recovers, chains, plans, loads, sandboxes, injects memory, or
schedules. It NEVER lets an exception propagate — any failure (unloaded skill,
missing interface, skill raising) becomes a structured ExecutionResult. Depends
only on the Phase 8.5 LoadedSkill.

Canonical interface: skills expose ``run(context)`` (Phase 8.6 standardization).
A skill carrying only a legacy ``execute`` is bridged by a minimal shim here so
the single canonical call site stays uniform.
"""

from __future__ import annotations

from brain.skill_runtime.interfaces import ISkillExecutor
from brain.skill_runtime.models import ExecutionResult, LoadedSkill

_CANONICAL = "run"
_LEGACY = "execute"


class SkillExecutor(ISkillExecutor):
    """Runs one loaded skill; converts every failure into ExecutionResult."""

    def execute(self, loaded: LoadedSkill, context: object = None) -> ExecutionResult:
        key = loaded.skill.registry_key if loaded.skill else ""

        if not loaded.loaded or loaded.instance is None:
            return ExecutionResult(
                succeeded=False, registry_key=key, error="not_loaded"
            )

        entry = self._entrypoint(loaded.instance)
        if entry is None:
            return ExecutionResult(
                succeeded=False, registry_key=key, error="no_entrypoint"
            )

        # Single call. Any exception is captured — never propagated.
        try:
            output = entry(context)
        except Exception as e:  # noqa: BLE001 — failure-safe by contract
            return ExecutionResult(
                succeeded=False, registry_key=key,
                error=f"execution_failed: {type(e).__name__}",
            )

        return ExecutionResult(succeeded=True, output=output, registry_key=key)

    @staticmethod
    def _entrypoint(instance: object):
        # Canonical run() first; minimal legacy execute() shim otherwise.
        fn = getattr(instance, _CANONICAL, None)
        if callable(fn):
            return fn
        fn = getattr(instance, _LEGACY, None)
        if callable(fn):
            return fn
        return None
