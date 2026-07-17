"""
brain/skills/manager.py — Phase 5.2 SkillManager

Task → registry lookup → choose executor → execute → SkillResult.

Contains NO planning, NO reflection, NO memory. Executors and the registry
are injected (DI-constructed in Bootstrapper). Never raises out of
execute(): every failure mode maps to a failed SkillResult so callers get
one uniform contract.
"""

from __future__ import annotations

from typing import Any, List, Optional

from brain.core.models import Task
from brain.skills.models import SkillResult
from brain.skills.registry import SkillRegistry


class SkillManager:
    """Resolves and runs skills by id via provider-matched executors."""

    def __init__(self, registry: SkillRegistry, executors: Optional[List[Any]] = None) -> None:
        self._registry = registry
        self._executors: List[Any] = list(executors or [])

    def resolve_executor(self, spec) -> Optional[Any]:
        """Return the first executor that supports *spec*, or None."""
        for executor in self._executors:
            if executor.supports(spec):
                return executor
        return None

    async def execute(self, task: Task) -> SkillResult:
        """
        Execute one Task.

        Failure modes (all non-raising):
          - task has no skill_id      → ok=False
          - skill_id not in registry  → ok=False
          - no executor for provider  → ok=False
        """
        if not task.skill_id:
            return SkillResult(
                skill_id="", ok=False,
                error=f"Task '{task.id}' has no skill_id bound.",
            )
        spec = self._registry.get(task.skill_id)
        if spec is None:
            return SkillResult(
                skill_id=task.skill_id, ok=False,
                error=f"Skill '{task.skill_id}' is not registered.",
            )
        executor = self.resolve_executor(spec)
        if executor is None:
            return SkillResult(
                skill_id=spec.id, ok=False,
                error=f"No executor available for provider '{spec.provider}'.",
            )
        return await executor.run(spec, dict(task.params))
