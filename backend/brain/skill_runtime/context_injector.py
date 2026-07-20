"""
brain/skill_runtime/context_injector.py — Phase 8.7: ContextInjector

Prepares everything a skill needs BEFORE execution. Pure transformation:

    LoadedSkill + caller data → immutable ExecutionContext → ContextInjectionResult

It does NOTHING else — never loads, executes, retries, recovers, chains,
schedules, accesses the registry, imports skill_creator, plans, writes memory,
or runs tools/network/subprocess. Depends only on the Phase 8.5 LoadedSkill,
caller-supplied data, and skill_runtime models.

Inputs are never mutated: supplied snapshot/variable/metadata dicts are copied
into the frozen ExecutionContext (plain read-only data — no live services, no
runtime objects, no raw skill instance). The raw LoadedSkill.instance is NOT
read here; only the skill's identity (registry_key) crosses into the context.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from brain.skill_runtime.interfaces import IContextInjector
from brain.skill_runtime.models import (
    ContextInjectionResult,
    ExecutionContext,
    LoadedSkill,
)


class ContextInjector(IContextInjector):
    """Deterministic, pure builder of an immutable ExecutionContext."""

    def inject(
        self,
        loaded: LoadedSkill,
        *,
        conversation_id: str = "",
        user_input: str = "",
        memory_snapshot: Optional[dict] = None,
        workspace_snapshot: Optional[dict] = None,
        environment_snapshot: Optional[dict] = None,
        available_tools: Optional[Tuple[str, ...]] = None,
        variables: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> ContextInjectionResult:
        if not loaded.loaded:
            return ContextInjectionResult(prepared=False, reason="not_loaded")
        if loaded.skill is None:
            return ContextInjectionResult(prepared=False, reason="no_skill")

        context = ExecutionContext(
            registry_key=loaded.skill.registry_key,
            conversation_id=conversation_id,
            user_input=user_input,
            memory_snapshot=self._copy(memory_snapshot),
            workspace_snapshot=self._copy(workspace_snapshot),
            environment_snapshot=self._copy(environment_snapshot),
            available_tools=tuple(available_tools) if available_tools else (),
            variables=self._copy(variables),
            metadata=self._copy(metadata),
        )
        return ContextInjectionResult(prepared=True, context=context, reason="prepared")

    @staticmethod
    def _copy(value: Optional[dict]) -> Dict[str, Any]:
        # Shallow copy so the caller's dict is never aliased into the frozen
        # context; inputs are never mutated.
        return dict(value) if value else {}
