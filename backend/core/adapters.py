"""
core/adapters.py — Lumina V2 Infrastructure Adapters (Phase 1.6)

Thin pass-through adapters that sit between legacy runtime code and the
Phase 1.0-1.5 architecture. Each adapter wraps one existing service and
forwards every call to it unchanged — same arguments, same return values,
same exceptions, same order. No adapter contains business logic or
transforms data; each has exactly one responsibility (adapt one interface
to one wrapped implementation).

Nothing in the existing runtime path resolves or calls these adapters
yet. They are registered in the container purely as additional,
coexisting resolution paths — legacy globals and direct service access
are untouched.
"""

from __future__ import annotations

from typing import Any

from core.interfaces import IBrainState, IEventBus, IExecutionContext, IPipeline


class BrainStateAdapter(IBrainState):
    """Forwards every call to a wrapped IBrainState implementation."""

    def __init__(self, brain_state: IBrainState) -> None:
        self._brain_state = brain_state

    def snapshot(self) -> Any:
        return self._brain_state.snapshot()

    def transaction(self) -> Any:
        return self._brain_state.transaction()

    def reset_session(self) -> None:
        self._brain_state.reset_session()

    def get_status(self) -> Any:
        return self._brain_state.get_status()


class EventBusAdapter(IEventBus):
    """Forwards every call to a wrapped IEventBus implementation."""

    def __init__(self, event_bus: IEventBus) -> None:
        self._event_bus = event_bus

    async def publish(self, topic: str, payload: dict, priority: str = "MEDIUM") -> None:
        await self._event_bus.publish(topic, payload, priority)

    async def subscribe(self, topic: str, callback: Any) -> Any:
        return await self._event_bus.subscribe(topic, callback)

    async def unsubscribe(self, token: Any) -> None:
        await self._event_bus.unsubscribe(token)


class ExecutionContextAdapter(IExecutionContext):
    """
    Forwards every call to a wrapped IExecutionContext implementation.

    child() returns another ExecutionContextAdapter wrapping the newly
    derived context, so the adapter boundary is preserved across
    derivation the same way it is at construction.
    """

    def __init__(self, execution_context: IExecutionContext) -> None:
        self._execution_context = execution_context

    def child(self, **overrides: Any) -> "ExecutionContextAdapter":
        return ExecutionContextAdapter(self._execution_context.child(**overrides))

    def __getattr__(self, name: str) -> Any:
        # Read-only forwarding of fields (context_id, session_id, etc.)
        # not part of the IExecutionContext contract itself.
        return getattr(self._execution_context, name)


class PipelineAdapter(IPipeline):
    """Forwards every call to a wrapped IPipeline implementation."""

    def __init__(self, pipeline: IPipeline) -> None:
        self._pipeline = pipeline

    def register(self, middleware: Any) -> None:
        self._pipeline.register(middleware)

    def remove(self, middleware: Any) -> None:
        self._pipeline.remove(middleware)

    async def execute(self, context: Any) -> Any:
        return await self._pipeline.execute(context)

    def clear(self) -> None:
        self._pipeline.clear()
