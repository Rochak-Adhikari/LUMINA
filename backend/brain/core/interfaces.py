"""
brain/core/interfaces.py — Phase 5.1 cognitive contracts

Abstract interfaces for the BrainCore layer. Same rules as
core/interfaces.py: behaviour only, no implementation details, no imports
from concrete runtime modules.

Phase 5.2 adds IPlanner. Later milestones add ISkillRegistry/ISkillManager
abstractions if needed, plus IReflectionEngine and IEvolutionEngine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from brain.core.models import BrainContext, BrainRequest, BrainResult, Plan


class IContextBuilder(ABC):
    """
    Assembles a BrainContext for a BrainRequest.

    Implementors:  ContextBuilder (backend/brain/core/context_builder.py)

    The builder READS from its collaborators (BrainState snapshot, and in
    later milestones memory/workspace/persona) and never mutates anything.
    """

    @abstractmethod
    def build(self, request: BrainRequest) -> BrainContext:
        """Return a frozen BrainContext for *request*."""


class IPlanner(ABC):
    """
    Produces a Plan from a BrainContext — or None when the request is not
    recognized (Phase 5.2 contract: unknown requests yield no Plan).

    Implementors:  RulePlanner (backend/brain/planning/rule_planner.py)

    Planners plan only. They never execute, never know executor types,
    and never touch MCP/tools.
    """

    @abstractmethod
    def plan(self, context: BrainContext) -> Optional[Plan]:
        """Return a Plan for *context*, or None if not recognized."""


class IBrainCore(ABC):
    """
    The single cognitive orchestrator.

    Implementors:  BrainCore (backend/brain/core/brain_core.py)

    BrainCore sequences the cognitive pipeline (context → plan → execute →
    reflect → respond). It contains NO business logic itself — each stage
    is delegated to a collaborator. In Phase 5.1 only the context stage
    exists; handle() builds context and returns a pass-through result.
    """

    @abstractmethod
    async def handle(self, request: BrainRequest) -> BrainResult:
        """Process one BrainRequest through the cognitive pipeline."""
