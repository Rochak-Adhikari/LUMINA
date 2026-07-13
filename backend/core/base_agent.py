"""
Base agent interface for Lumina.

Inspired by OpenJarvis agent abstractions. Provides a common interface
that existing agents (CadAgent, KasaAgent, etc.) can optionally adopt,
and new agents SHOULD implement.

Existing agents are NOT required to subclass this immediately — they
can be wrapped with adapters when needed. This is purely additive.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentContext:
    """Context passed to an agent when executing a task."""
    user_input: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    project_path: Optional[str] = None
    permissions: Dict[str, bool] = field(default_factory=dict)
    memory_store: Any = None
    session: Any = None


@dataclass
class AgentResult:
    """Standard result returned by an agent."""
    success: bool = False
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def __str__(self) -> str:
        if self.success:
            return self.message or "OK"
        return self.error or self.message or "Failed"


class BaseAgent(ABC):
    """Abstract base class for Lumina agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent (e.g. 'cad', 'kasa', 'printer')."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description of what this agent does."""
        return ""

    @property
    def required_tools(self) -> List[str]:
        """List of Gemini tool names this agent handles."""
        return []

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent's primary task given a context."""
        ...

    async def health_check(self) -> bool:
        """Optional health check. Returns True if agent is functional."""
        return True

    def stop(self) -> None:
        """Optional cleanup when the agent is being shut down."""
        pass
