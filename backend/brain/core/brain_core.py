"""
brain/core/brain_core.py — Phase 5.1 BrainCore orchestrator

The single cognitive orchestration authority. BrainCore sequences the
pipeline; it never contains business logic, planning, tool execution,
memory mutation, reflection, or evolution — those are collaborator
responsibilities added in later milestones.

Phase 5.1 pipeline (skeleton):
    handle(request)
      1. Build BrainContext (ContextBuilder)
      2. Return a pass-through BrainResult (handled=False)

No runtime path calls this yet. Registered in DI by Bootstrapper and
exposed via RuntimeFacade only.
"""

from __future__ import annotations

from typing import Optional

from core.interfaces import IEventBus
from brain.core.interfaces import IBrainCore, IContextBuilder
from brain.core.models import BrainRequest, BrainResult


class BrainCore(IBrainCore):
    """
    Orchestrator skeleton.

    Collaborators (Phase 5.1):
      context_builder — required; builds BrainContext per request.
      event_bus       — optional; publishes lifecycle events (non-fatal
                        if publishing fails or bus is absent).
    """

    def __init__(
        self,
        context_builder: IContextBuilder,
        event_bus: Optional[IEventBus] = None,
    ) -> None:
        self._context_builder = context_builder
        self._event_bus = event_bus

    async def handle(self, request: BrainRequest) -> BrainResult:
        """
        Process one BrainRequest.

        Phase 5.1: builds context, publishes an observability event, and
        returns a pass-through result. handled=False signals to callers
        that no cognition occurred (planning/execution arrive in 5.2+).
        """
        context = self._context_builder.build(request)

        if self._event_bus is not None:
            try:
                await self._event_bus.publish(
                    "brain.request_received",
                    {
                        "request_id": request.request_id,
                        "channel": request.channel,
                    },
                )
            except Exception:
                # Observability only — never let event publishing break
                # the pipeline (same policy as server.py event publishes).
                pass

        return BrainResult(
            request_id=context.request.request_id,
            response_text="",
            handled=False,
        )
