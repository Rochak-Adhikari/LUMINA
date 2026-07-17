"""
core/services.py — Lumina V2 Service Resolution Helpers (Phase 1.7 + Phase 3 + Phase 4.5)

A single, centralized set of strongly typed accessors for resolving
services from the DependencyContainer. This module exists only to reduce
future coupling: runtime code calls `get_brain_state()` instead of
`container.resolve(IBrainState)` directly, so the resolution call site
is centralized in one place.

Phase 3 additions:
  - get_knowledge_manager()  — IKnowledgeManager resolution
  - get_session_manager()    — SessionManager resolution
  - get_service_accessor()   — ServiceAccessor resolution

Phase 4.5 additions:
  - get_application_host()   — ApplicationHost resolution

This module does NOT:
  - cache anything (every call resolves fresh from the container; caching
    behaviour, if any, belongs entirely to the container itself)
  - contain business logic
  - manage lifecycle (construction/registration is Bootstrapper's job)
  - invent services that don't already exist in the container

Each accessor is a one-line wrapper: `container.resolve(SomeType)`. The
container parameter defaults to the process-level `container` singleton
(core/container.py) but can be overridden for testing.
"""

from __future__ import annotations

from core.container import DependencyContainer, container as _default_container
from core.interfaces import IBrainState, IEventBus, IPipeline, IMemoryManager, IWorkspaceManager, IKnowledgeManager
from core.context import ExecutionContextFactory
from core.adapters import (
    BrainStateAdapter,
    EventBusAdapter,
    ExecutionContextAdapter,
    PipelineAdapter,
)


def get_memory_manager(c: DependencyContainer = _default_container) -> IMemoryManager:
    """Resolve the registered IMemoryManager implementation."""
    return c.resolve(IMemoryManager)


def get_workspace_manager(c: DependencyContainer = _default_container) -> IWorkspaceManager:
    """Resolve the registered IWorkspaceManager implementation."""
    return c.resolve(IWorkspaceManager)


def get_knowledge_manager(c: DependencyContainer = _default_container) -> IKnowledgeManager:
    """Resolve the registered IKnowledgeManager implementation."""
    return c.resolve(IKnowledgeManager)


def get_brain_state(c: DependencyContainer = _default_container) -> IBrainState:
    """Resolve the registered IBrainState implementation."""
    return c.resolve(IBrainState)


def get_event_bus(c: DependencyContainer = _default_container) -> IEventBus:
    """Resolve the registered IEventBus implementation."""
    return c.resolve(IEventBus)


def get_execution_context_factory(
    c: DependencyContainer = _default_container,
) -> ExecutionContextFactory:
    """Resolve the registered ExecutionContextFactory."""
    return c.resolve(ExecutionContextFactory)


def get_pipeline(c: DependencyContainer = _default_container) -> IPipeline:
    """Resolve the registered IPipeline (RequestPipeline) implementation."""
    return c.resolve(IPipeline)


def get_brain_state_adapter(c: DependencyContainer = _default_container) -> BrainStateAdapter:
    """Resolve the registered BrainStateAdapter."""
    return c.resolve(BrainStateAdapter)


def get_event_bus_adapter(c: DependencyContainer = _default_container) -> EventBusAdapter:
    """Resolve the registered EventBusAdapter."""
    return c.resolve(EventBusAdapter)


def get_pipeline_adapter(c: DependencyContainer = _default_container) -> PipelineAdapter:
    """Resolve the registered PipelineAdapter."""
    return c.resolve(PipelineAdapter)


def get_execution_context_adapter(
    c: DependencyContainer = _default_container,
) -> ExecutionContextAdapter:
    """
    Resolve an ExecutionContextAdapter.

    Registered as transient (Phase 1.6) — each call returns a fresh
    adapter wrapping a new root ExecutionContext.
    """
    return c.resolve(ExecutionContextAdapter)


# ---- Phase 3 Session & Service Accessor resolvers ----------------------

def get_session_manager(c: DependencyContainer = _default_container):
    """Resolve the registered SessionManager."""
    from core.session import SessionManager
    return c.resolve(SessionManager)


def get_service_accessor(c: DependencyContainer = _default_container):
    """Resolve the registered ServiceAccessor."""
    from core.service_accessor import ServiceAccessor
    return c.resolve(ServiceAccessor)


# ---- Phase 4.5 Lifecycle resolver ---------------------------------------

def get_application_host(c: DependencyContainer = _default_container):
    """Resolve the registered ApplicationHost."""
    from core.application import ApplicationHost
    return c.resolve(ApplicationHost)
