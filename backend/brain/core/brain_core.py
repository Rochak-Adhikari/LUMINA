"""
brain/core/brain_core.py — BrainCore orchestrator (Phase 5.4 Step 4)

The single cognitive orchestration authority. BrainCore sequences the
pipeline; it never contains business logic, planning, tool execution,
memory mutation, reflection, or evolution — those are collaborator
responsibilities.

Pipeline:
    handle(request)
      1. Build BrainContext (ContextBuilder)
      2. Plan (injected planner — PlannerChain: Rule → LLM)
      3. Execute each task (injected SkillManager)
      4. Aggregate a BrainResult

handled semantics (Phase 5.4 Step 4):
  - No planner/manager injected, or plan is None   → handled=False (declined;
    the caller falls through to the legacy path).
  - Plan produced AND every task succeeds          → handled=True, plan set.
  - Plan produced but any task fails               → handled=False (declined;
    plan not attached — the legacy path handles the request).

This keeps the layer DORMANT-SAFE: with the LegacyToolExecutor unbound (no
live session), execution always fails, so handle() returns handled=False —
identical to the skeleton's external contract. handled=True only occurs once
a live dispatch is bound (Step 6). No runtime path calls handle() yet.
"""

from __future__ import annotations

from typing import Any, List, Optional

from core.interfaces import IEventBus
from brain.core.interfaces import IBrainCore, IContextBuilder
from brain.core.models import BrainRequest, BrainResult, Reflection


class BrainCore(IBrainCore):
    """
    Cognitive orchestrator.

    Collaborators (all injected):
      context_builder   — required; builds BrainContext per request.
      event_bus         — optional; publishes lifecycle events (non-fatal).
      planner           — optional; produces a Plan (PlannerChain). When absent,
                          handle() is a pass-through (handled=False).
      skill_manager     — optional; executes a Task -> SkillResult. When absent,
                          handle() is a pass-through (handled=False).
      reflection_engine — optional; read-only post-execution evaluator (5.7.4).
                          After execution finishes, produces a Reflection
                          attached to BrainResult.reflection. Never affects
                          handling; failure inside it is swallowed (→ None).
    """

    def __init__(
        self,
        context_builder: IContextBuilder,
        event_bus: Optional[IEventBus] = None,
        planner: Optional[Any] = None,
        skill_manager: Optional[Any] = None,
        reflection_engine: Optional[Any] = None,
    ) -> None:
        self._context_builder = context_builder
        self._event_bus = event_bus
        self._planner = planner
        self._skill_manager = skill_manager
        self._reflection_engine = reflection_engine

    async def handle(self, request: BrainRequest) -> BrainResult:
        """Process one BrainRequest (see module docstring for handled semantics)."""
        context = self._context_builder.build(request)
        await self._publish("brain.request_received", request)

        # No cognition collaborators → pass-through (declined).
        if self._planner is None or self._skill_manager is None:
            return BrainResult(request_id=request.request_id, handled=False)

        # 1. Plan (prefer the async path; fall back to sync plan()).
        plan_fn = getattr(self._planner, "plan_async", None)
        try:
            if plan_fn is not None:
                plan = await plan_fn(context)
            else:
                plan = self._planner.plan(context)
        except Exception:
            plan = None

        if plan is None or not plan.tasks:
            # Unrecognized → decline; the legacy path handles it.
            return BrainResult(request_id=request.request_id, handled=False)

        await self._publish("brain.plan_created", request)

        # 2. Execute each task via SkillManager (never raises).
        results: List[Any] = []
        for task in plan.tasks:
            results.append(await self._skill_manager.execute(task))

        # Reflection (5.7.4): read-only, exactly once, after execution. Never
        # affects handling; failure → reflection=None.
        reflection = self._reflect(request, plan, results, context)

        # 3. Aggregate. Full success → handled; otherwise decline (fall
        #    through to legacy). Plan attached only when handled.
        if results and all(getattr(r, "ok", False) for r in results):
            await self._publish("brain.request_handled", request)
            return BrainResult(
                request_id=request.request_id,
                handled=True,
                plan=plan,
                artifacts={"results": [getattr(r, "output", None) for r in results]},
                reflection=reflection,
            )

        return BrainResult(
            request_id=request.request_id,
            handled=False,
            reflection=reflection,
        )

    def _reflect(self, request, plan, results, context) -> Optional[Reflection]:
        """Produce a Reflection for a completed request; never raise. Read-only.
        Returns None when no engine is injected or the engine fails."""
        if self._reflection_engine is None:
            return None
        try:
            return self._reflection_engine.reflect(request, plan, results, context)
        except Exception:
            return None

    async def _publish(self, topic: str, request: BrainRequest) -> None:
        """Best-effort event publish — never breaks the pipeline."""
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                topic,
                {"request_id": request.request_id, "channel": request.channel},
            )
        except Exception:
            pass
