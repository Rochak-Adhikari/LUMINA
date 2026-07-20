"""Lumina core — registries, base classes, shared types, and DI container."""

from core.registry import (
    ActionRegistry,
    AgentRegistry,
    ToolRegistry,
    ToolDispatcherRegistry,
)

# Phase 5.4 Order 4 (D2): the `import core.tool_handlers` side-effect import
# (which registers Tier-1 handlers AND drags the Gemini SDK) was relocated to
# core/bootstrap.py so the core package no longer transitively imports a model
# SDK. bootstrap.py runs once at startup before any tool dispatch, so Tier-1
# registration is unchanged. Tests that need the handlers import it directly.

# Phase 1.1 — Interface layer and DI container
from core.interfaces import (
    IBrainState,           # Phase 1.2
    IMemoryManager,
    IKnowledgeManager,
    IWorkspaceManager,
    IModelGateway,
    IEventBus,
)
from core.container import container

__all__ = [
    # Registries (Phase 1)
    "ActionRegistry",
    "AgentRegistry",
    "ToolRegistry",
    "ToolDispatcherRegistry",
    # Interfaces (Phase 1.1)
    "IMemoryManager",
    "IKnowledgeManager",
    "IWorkspaceManager",
    "IModelGateway",
    "IEventBus",
    # Interfaces (Phase 1.2)
    "IBrainState",
    # DI Container (Phase 1.1)
    "container",
]
