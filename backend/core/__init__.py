"""Lumina core — registries, base classes, shared types, and DI container."""

from core.registry import (
    ActionRegistry,
    AgentRegistry,
    ToolRegistry,
    ToolDispatcherRegistry,
)
import core.tool_handlers

# Phase 1.1 — Interface layer and DI container
from core.interfaces import (
    IBrainState,           # Phase 1.2
    IMemoryManager,
    IKnowledgeManager,
    IWorkspaceManager,
    ISmartHomeAgent,
    ICadAgent,
    IPrinterAgent,
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
    "ISmartHomeAgent",
    "ICadAgent",
    "IPrinterAgent",
    "IModelGateway",
    "IEventBus",
    # Interfaces (Phase 1.2)
    "IBrainState",
    # DI Container (Phase 1.1)
    "container",
]
