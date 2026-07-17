"""
brain/core — Lumina Cognitive Architecture: BrainCore package (Phase 5.1)

Architectural skeleton only. This package establishes the orchestration
foundation that later Phase 5 milestones (Planner, Skill Registry, Skill
Manager, Reflection, Evolution) plug into.

Phase 5.1 contents:
  - models.py           BrainRequest / BrainContext / BrainResult / Plan /
                        Task / Reflection (pydantic value objects, no logic)
  - interfaces.py       IBrainCore / IContextBuilder contracts
  - context_builder.py  ContextBuilder — assembles BrainContext
  - brain_core.py       BrainCore — orchestrator (context → result only)

Nothing in this package is wired into any runtime path yet. Registration
is DI-only (Bootstrapper); access is RuntimeFacade-only.
"""

from brain.core.models import (
    BrainRequest,
    BrainContext,
    BrainResult,
    Plan,
    Task,
    Reflection,
)
from brain.core.interfaces import IBrainCore, IContextBuilder
from brain.core.context_builder import ContextBuilder
from brain.core.brain_core import BrainCore

__all__ = [
    "BrainRequest",
    "BrainContext",
    "BrainResult",
    "Plan",
    "Task",
    "Reflection",
    "IBrainCore",
    "IContextBuilder",
    "ContextBuilder",
    "BrainCore",
]
