"""
core/services.py — Lumina V2 Service Resolution Helpers (Phase 1.7)

A single, centralized set of strongly typed accessors for resolving
services from the DependencyContainer. This module exists only to reduce
future coupling: once runtime code is migrated (a later phase), it should
call `get_brain_state()` instead of `container.resolve(IBrainState)`
directly, so the resolution call site is centralized in one place.

This module does NOT:
  - cache anything (every call resolves fresh from the container; caching
    behaviour, if any, belongs entirely to the container itself)
  - contain business logic
  - manage lifecycle (construction/registration is Bootstrapper's job)
  - invent services that don't already exist in the container

Each accessor is a one-line wrapper: `container.resolve(SomeType)`. The
container parameter defaults to the process-level `container` singleton
(core/container.py) but can be overridden for testing.

Nothing in the existing runtime path calls these accessors yet — this is
infrastructure only, matching the scope of Phase 1.6's adapters.
"""

from __future__ import annotations

from core.container import DependencyContainer, container as _default_container
from core.interfaces import IBrainState, IEventBus, IPipeline
from core.context import ExecutionContextFactory
from core.adapters import (
    BrainStateAdapter,
    EventBusAdapter,
    ExecutionContextAdapter,
    PipelineAdapter,
)


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
