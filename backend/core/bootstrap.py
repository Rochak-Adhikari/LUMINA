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
from core.adapters import BrainStateAdapter, EventBusAdapter, ExecutionContextAdapter, PipelineAdapter
from core.metadata import (
    ServiceMetadata,
    ServiceMetadataRegistry,
    LIFECYCLE_INSTANCE,
    LIFECYCLE_TRANSIENT,
)


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
        self.brain_state_adapter: Optional[BrainStateAdapter] = None
        self.event_bus_adapter: Optional[EventBusAdapter] = None
        self.pipeline_adapter: Optional[PipelineAdapter] = None
        self.metadata_registry: Optional[ServiceMetadataRegistry] = None

    def bootstrap(self) -> None:
        """Construct and register all services owned by this bootstrapper."""
        self._register_smart_home_agent()
        self._register_brain_state()
        self._register_event_bus()
        self._register_execution_context_factory()
        self._register_pipeline()
        self._register_adapters()
        self._register_service_metadata()

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

    def _register_adapters(self) -> None:
        """
        Register thin pass-through adapters alongside the legacy/concrete
        services they wrap.

        These do NOT replace the existing IBrainState/IEventBus/IPipeline
        registrations above — they are registered under their own
        concrete adapter types so both resolution paths coexist. Nothing
        in the current runtime resolves these types yet.

        ExecutionContextAdapter has no single long-lived instance to wrap
        (execution contexts are per-request), so it is registered as a
        transient: each resolve() wraps a fresh root context from
        ExecutionContextFactory.
        """
        self.brain_state_adapter = BrainStateAdapter(self.brain_state)
        self._container.register_instance(BrainStateAdapter, self.brain_state_adapter)
        print("[DI] BrainStateAdapter registered")

        self.event_bus_adapter = EventBusAdapter(self.event_bus)
        self._container.register_instance(EventBusAdapter, self.event_bus_adapter)
        print("[DI] EventBusAdapter registered")

        self.pipeline_adapter = PipelineAdapter(self.pipeline)
        self._container.register_instance(PipelineAdapter, self.pipeline_adapter)
        print("[DI] PipelineAdapter registered")

        self._container.register_transient(
            ExecutionContextAdapter,
            lambda: ExecutionContextAdapter(self.context_factory.create()),
        )
        print("[DI] ExecutionContextAdapter registered (transient)")

    def _register_service_metadata(self) -> None:
        """
        Populate a ServiceMetadataRegistry describing the infrastructure
        services registered above, and register the registry itself into
        the container.

        This is descriptive/introspection data only (Phase 1.8). It does
        not change how any service is registered or resolved.
        """
        registry = ServiceMetadataRegistry()
        records = [
            ServiceMetadata(
                name="BrainState", key=repr(IBrainState),
                lifecycle=LIFECYCLE_INSTANCE, owner="Phase 1.2",
                description="Single thread-safe source of runtime truth.",
            ),
            ServiceMetadata(
                name="EventBus", key=repr(IEventBus),
                lifecycle=LIFECYCLE_INSTANCE, owner="Phase 1.2",
                description="In-process publish/subscribe event bus.",
            ),
            ServiceMetadata(
                name="ExecutionContextFactory", key=repr(ExecutionContextFactory),
                lifecycle=LIFECYCLE_INSTANCE, owner="Phase 1.4",
                description="Factory for immutable execution contexts.",
            ),
            ServiceMetadata(
                name="RequestPipeline", key=repr(IPipeline),
                lifecycle=LIFECYCLE_INSTANCE, owner="Phase 1.5",
                description="Sealed, ordered middleware execution pipeline.",
            ),
            ServiceMetadata(
                name="BrainStateAdapter", key=repr(BrainStateAdapter),
                lifecycle=LIFECYCLE_INSTANCE, owner="Phase 1.6",
                description="Pass-through adapter over IBrainState.",
            ),
            ServiceMetadata(
                name="EventBusAdapter", key=repr(EventBusAdapter),
                lifecycle=LIFECYCLE_INSTANCE, owner="Phase 1.6",
                description="Pass-through adapter over IEventBus.",
            ),
            ServiceMetadata(
                name="PipelineAdapter", key=repr(PipelineAdapter),
                lifecycle=LIFECYCLE_INSTANCE, owner="Phase 1.6",
                description="Pass-through adapter over IPipeline.",
            ),
            ServiceMetadata(
                name="ExecutionContextAdapter", key=repr(ExecutionContextAdapter),
                lifecycle=LIFECYCLE_TRANSIENT, owner="Phase 1.6",
                description="Per-request pass-through adapter over an execution context.",
            ),
        ]
        for record in records:
            registry.register(record)

        self.metadata_registry = registry
        self._container.register_instance(ServiceMetadataRegistry, registry)
        print(f"[DI] ServiceMetadataRegistry registered ({len(registry)} records)")
