"""
core/bootstrap.py — Lumina V2 Service Construction Layer (Phase 1.3)

Bootstrapper's only job is to construct services and register them into the
DI container. It contains no runtime/business logic and makes no decisions
beyond "does this optional service exist, yes or no."

This replaces the scattered container.register_* calls that previously lived
inline in server.py's module-level startup code. The objects constructed and
the order they are registered in are unchanged from the prior inline code.
"""

from __future__ import annotations

from typing import Any, Optional

from core.container import DependencyContainer
from core.interfaces import IBrainState, IEventBus, IPipeline, ISmartHomeAgent
from brain.state import BrainState
from brain.events import InProcessEventBus
from core.context import ExecutionContextFactory
from core.pipeline import PipelineBuilder, RequestPipeline


class Bootstrapper:
    """
    Constructs core services and wires them into the container.

    kasa_agent is passed in already-constructed (or None) because its
    construction depends on settings resolved earlier in server.py's
    startup sequence — Bootstrapper only registers it, it does not decide
    whether it should exist.
    """

    def __init__(self, container: DependencyContainer, kasa_agent: Optional[Any] = None) -> None:
        self._container = container
        self._kasa_agent = kasa_agent
        self.brain_state: Optional[BrainState] = None
        self.event_bus: Optional[InProcessEventBus] = None
        self.context_factory: Optional[ExecutionContextFactory] = None
        self.pipeline: Optional[RequestPipeline] = None

    def bootstrap(self) -> None:
        """Construct and register all services owned by this bootstrapper."""
        self._register_smart_home_agent()
        self._register_brain_state()
        self._register_event_bus()
        self._register_execution_context_factory()
        self._register_pipeline()

    def _register_smart_home_agent(self) -> None:
        if self._kasa_agent is not None:
            self._container.register_instance(ISmartHomeAgent, self._kasa_agent)
            print("[DI] ISmartHomeAgent -> KasaAgent registered")
        else:
            print("[DI] ISmartHomeAgent - skipped (Kasa tools disabled)")

    def _register_brain_state(self) -> None:
        self.brain_state = BrainState()
        self._container.register_instance(IBrainState, self.brain_state)
        print("[DI] IBrainState -> BrainState registered")

    def _register_event_bus(self) -> None:
        self.event_bus = InProcessEventBus()
        self._container.register_instance(IEventBus, self.event_bus)
        print("[DI] IEventBus -> InProcessEventBus registered")

    def _register_execution_context_factory(self) -> None:
        self.context_factory = ExecutionContextFactory()
        self._container.register_instance(ExecutionContextFactory, self.context_factory)
        print("[DI] ExecutionContextFactory registered")

    def _register_pipeline(self) -> None:
        """
        Build and seal a RequestPipeline via PipelineBuilder.

        No middleware is registered — Phase 1.5 establishes the
        infrastructure only. The pipeline is fully built and immutable by
        the time this method returns; nothing in the existing runtime
        path resolves or calls it.
        """
        builder = PipelineBuilder()
        self.pipeline = builder.build()
        self._container.register_instance(IPipeline, self.pipeline)
        print("[DI] IPipeline -> RequestPipeline registered (sealed, no middleware)")
