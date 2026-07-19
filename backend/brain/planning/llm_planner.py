"""
brain/planning/llm_planner.py — Phase 5.3 LLMPlanner + PlannerChain

LLMPlanner converts free-form requests into Plan objects using an INJECTED
model abstraction (core.interfaces.IModelGateway). It:

  - NEVER imports any model SDK (google.genai / OpenAI / Anthropic / ...)
  - NEVER executes anything (no SkillManager, no tools, no server.py)
  - NEVER raises out of plan() — every failure mode returns None
  - is INERT when no gateway is bound (Phase 5.3 registers it unbound
    because no IModelGateway implementation exists in the repository yet)

PlannerChain implements the milestone's fallback architecture:

    BrainContext -> RulePlanner -> (None?) -> LLMPlanner -> Plan | None

It is registered under its own DI key; the IPlanner binding remains
RulePlanner until runtime wiring (a later milestone) flips it.
"""

from __future__ import annotations

import json
import re
from typing import Any, List, Optional

from core.interfaces import IModelGateway
from brain.core.interfaces import IPlanner
from brain.core.models import BrainContext, Plan, Task
from brain.skills.registry import SkillRegistry
from brain.planning.prompt_builder import format_workspace_context

_SYSTEM_INSTRUCTION = (
    "You are Lumina's planning engine. Convert the user request into a JSON "
    "execution plan. You NEVER execute anything — you only plan.\n"
    "Respond with ONLY a JSON object, no prose, no markdown fences, shaped:\n"
    '{"tasks": [{"intent": "<short verb phrase>", "skill_id": "<id from the '
    'catalog or null>", "params": {<string keys>}}], '
    '"confidence": <0.0-1.0>, "rationale": "<one sentence>"}\n'
    "Rules: use ONLY skill_id values present in the catalog (or null when no "
    "skill fits). Order tasks by execution order. Keep params minimal JSON "
    'primitives. If the request cannot be planned at all, respond {"tasks": []}.'
)


class LLMPlanner(IPlanner):
    """
    Model-backed planner.

    Collaborators (all injected, all optional-safe):
      model_gateway — IModelGateway; None => planner is inert (returns None).
      skill_registry — read-only metadata source for the skill catalog.
    """

    def __init__(
        self,
        model_gateway: Optional[IModelGateway] = None,
        skill_registry: Optional[SkillRegistry] = None,
        temperature: float = 0.0,
    ) -> None:
        self._gateway = model_gateway
        self._registry = skill_registry
        self._temperature = temperature

    # ------------------------------------------------------------------
    # IPlanner
    # ------------------------------------------------------------------

    def plan(self, context: BrainContext) -> Optional[Plan]:
        """
        Produce a Plan for *context* via the injected model gateway (sync).

        Returns None when: no gateway bound, empty text, voice_tool request
        (pre-decided upstream), model failure, unparseable output, or the
        model itself returns an empty task list.

        NOTE: inside a running event loop, prefer plan_async(). The sync path
        cannot drive an async gateway from within a running loop (it would
        require a nested asyncio.run); in that case it returns None rather
        than raising (never-raise contract).
        """
        if self._gateway is None:
            return None
        text = (context.request.text or "").strip()
        if not text or context.request.tool_call is not None:
            return None

        prompt = self._build_prompt(text, context.prompt_workspace)
        try:
            raw = self._generate_sync(prompt)
        except Exception:
            return None
        return self._parse_plan(raw)

    async def plan_async(self, context: BrainContext) -> Optional[Plan]:
        """
        Async variant of plan() — safe to call from within a running event
        loop (fixes D4: no nested asyncio.run).

        Same guards and same never-raise contract as plan(). This is the path
        BrainCore uses when orchestrating inside the server loop.
        """
        if self._gateway is None:
            return None
        text = (context.request.text or "").strip()
        if not text or context.request.tool_call is not None:
            return None

        prompt = self._build_prompt(text, context.prompt_workspace)
        try:
            raw = await self._generate_async(prompt)
        except Exception:
            return None
        return self._parse_plan(raw)

    # ------------------------------------------------------------------
    # Internals (pure data transformation — no execution, no I/O beyond
    # the injected gateway call)
    # ------------------------------------------------------------------

    def _skill_catalog(self) -> List[dict]:
        if self._registry is None:
            return []
        return [
            {"id": s.id, "description": s.description, "tags": s.tags}
            for s in self._registry.all()
        ]

    def _build_prompt(self, text: str, prompt_workspace: Optional[Any] = None) -> str:
        catalog = json.dumps(self._skill_catalog(), ensure_ascii=False)
        workspace_section = format_workspace_context(prompt_workspace)
        return (
            f"Skill catalog:\n{catalog}\n"
            f"{workspace_section}"
            f"\nUser request:\n{text}"
        )

    def _generate_sync(self, prompt: str) -> str:
        """
        Call the gateway synchronously.

        IModelGateway.generate_text is declared async; when it returns an
        awaitable this method must drive it to completion. It may only do so
        (via asyncio.run) when NO event loop is running — driving an awaitable
        with a nested asyncio.run inside a running loop raises RuntimeError
        (D4). Inside a running loop, callers must use plan_async() instead;
        this method raises internally there and plan() maps it to None.
        A sync-returning gateway is also accepted.
        """
        outcome = self._gateway.generate_text(
            prompt,
            system_instruction=_SYSTEM_INSTRUCTION,
            temperature=self._temperature,
        )
        if hasattr(outcome, "__await__"):
            import asyncio
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                # No running loop — safe to drive the awaitable to completion.
                return asyncio.run(_await(outcome))
            # Running loop present — cannot nest asyncio.run. Signal the caller
            # (plan() catches this and returns None); use plan_async() here.
            raise RuntimeError(
                "LLMPlanner._generate_sync cannot drive an async gateway "
                "inside a running event loop; use plan_async()."
            )
        return outcome

    async def _generate_async(self, prompt: str) -> str:
        """
        Call the gateway and await an async result if needed. Loop-safe:
        never uses asyncio.run. Accepts both async and sync gateways.
        """
        outcome = self._gateway.generate_text(
            prompt,
            system_instruction=_SYSTEM_INSTRUCTION,
            temperature=self._temperature,
        )
        if hasattr(outcome, "__await__"):
            return await outcome
        return outcome

    def _parse_plan(self, raw: Any) -> Optional[Plan]:
        """Parse model output into a Plan. Any structural problem => None."""
        if not isinstance(raw, str) or not raw.strip():
            return None
        payload = _extract_json(raw)
        if not isinstance(payload, dict):
            return None
        tasks_data = payload.get("tasks")
        if not isinstance(tasks_data, list) or not tasks_data:
            return None

        known_ids = {s.id for s in self._registry.all()} if self._registry else set()
        tasks: List[Task] = []
        for entry in tasks_data:
            if not isinstance(entry, dict):
                return None
            intent = str(entry.get("intent") or "").strip()
            if not intent:
                return None
            skill_id = entry.get("skill_id")
            if skill_id is not None:
                skill_id = str(skill_id)
                if known_ids and skill_id not in known_ids:
                    # Hallucinated skill — keep the task but unbind it so
                    # nothing downstream can execute a nonexistent skill.
                    skill_id = None
            params = entry.get("params") or {}
            if not isinstance(params, dict):
                params = {}
            tasks.append(Task(intent=intent, skill_id=skill_id, params=params))

        try:
            confidence = float(payload.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = min(1.0, max(0.0, confidence))
        rationale = str(payload.get("rationale") or "LLMPlanner generated plan")

        return Plan(
            tasks=tasks,
            strategy="sequential",
            confidence=confidence,
            rationale=rationale,
        )


class PlannerChain(IPlanner):
    """
    Ordered fallback chain: first planner returning a Plan wins.

    Phase 5.3 composition (built in Bootstrapper): [RulePlanner, LLMPlanner].
    Registered under its own DI key — IPlanner still resolves RulePlanner
    until runtime wiring flips the binding in a later milestone.
    """

    def __init__(self, planners: List[IPlanner]) -> None:
        self._planners = list(planners)

    def plan(self, context: BrainContext) -> Optional[Plan]:
        for planner in self._planners:
            result = planner.plan(context)
            if result is not None:
                return result
        return None

    async def plan_async(self, context: BrainContext) -> Optional[Plan]:
        """
        Async variant of plan(). Awaits each planner's plan_async() when it
        offers one; otherwise falls back to its synchronous plan(). First
        non-None Plan wins. Loop-safe (no nested asyncio.run).
        """
        for planner in self._planners:
            fn = getattr(planner, "plan_async", None)
            if fn is not None:
                result = await fn(context)
            else:
                result = planner.plan(context)
            if result is not None:
                return result
        return None


async def _await(awaitable):
    return await awaitable


def _extract_json(raw: str) -> Optional[Any]:
    """Parse JSON, tolerating markdown code fences around the object."""
    candidate = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    try:
        return json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None
