"""
core/runtime_facade.py — Lumina V2 Runtime Facade (Phase 1.8 + Phase 3 + Phase 4.5)

A single, centralized, strongly typed access point for the infrastructure
services built in Phases 1.2–1.7 and extended in Phase 3.  Where Phase 1.7's
core/services.py provides free-function accessors, RuntimeFacade bundles them
behind one object that runtime code holds a reference to instead of reaching
into the container (or into legacy globals) directly.

Phase 3 additions:
  - knowledge_manager: IKnowledgeManager accessor
  - session_manager: SessionManager accessor
  - service_accessor: ServiceAccessor accessor

Phase 4.5 additions:
  - application_host: ApplicationHost accessor for unified lifecycle

This facade:
  - performs no caching (delegates every call to core/services.py, which
    delegates to the container)
  - contains no business logic, no AI/planner/memory/routing logic
  - manages no lifecycle (delegates to ApplicationHost)
"""

from __future__ import annotations

from typing import Any

from core.container import DependencyContainer, container as _default_container
from core.interfaces import (
    IBrainState, IEventBus, IPipeline, IMemoryManager,
    IWorkspaceManager, IKnowledgeManager,
)
from core.context import ExecutionContextFactory
from core.adapters import (
    BrainStateAdapter,
    EventBusAdapter,
    ExecutionContextAdapter,
    PipelineAdapter,
)
import core.services as services


class RuntimeFacade:
    """
    Centralized typed access to already-registered infrastructure services.

    Holds only a container reference; every accessor resolves fresh. The
    container defaults to the process-level singleton but can be injected
    for isolation in tests.

    Phase 4.5: exposes ApplicationHost for unified lifecycle coordination.
    """

    def __init__(self, container: DependencyContainer = _default_container) -> None:
        self._container = container

    # ---- Core services -------------------------------------------------

    @property
    def brain_state(self) -> IBrainState:
        return services.get_brain_state(self._container)

    @property
    def event_bus(self) -> IEventBus:
        return services.get_event_bus(self._container)

    @property
    def execution_context_factory(self) -> ExecutionContextFactory:
        return services.get_execution_context_factory(self._container)

    @property
    def pipeline(self) -> IPipeline:
        return services.get_pipeline(self._container)

    @property
    def memory_manager(self) -> IMemoryManager:
        return services.get_memory_manager(self._container)

    @property
    def workspace_manager(self) -> IWorkspaceManager:
        return services.get_workspace_manager(self._container)

    @property
    def knowledge_manager(self) -> IKnowledgeManager:
        """Resolve the registered IKnowledgeManager implementation."""
        return services.get_knowledge_manager(self._container)

    # ---- Phase 3: Session & Service Accessor ----------------------------

    @property
    def session_manager(self) -> Any:
        """Resolve the registered SessionManager."""
        return services.get_session_manager(self._container)

    @property
    def service_accessor(self) -> Any:
        """Resolve the registered ServiceAccessor."""
        return services.get_service_accessor(self._container)

    # ---- Phase 4.5: Application Lifecycle -------------------------------

    @property
    def application_host(self) -> Any:
        """Resolve the registered ApplicationHost for unified lifecycle."""
        return services.get_application_host(self._container)

    # ---- Phase 5.1: Cognitive Architecture ------------------------------

    @property
    def brain_core(self) -> Any:
        """
        Resolve the registered IBrainCore (BrainCore skeleton).

        Resolved directly from the container (import kept local to avoid
        widening core/services.py in Phase 5.1 — the free-function accessor
        can be added when a runtime path actually consumes BrainCore).
        """
        from brain.core.interfaces import IBrainCore
        return self._container.resolve(IBrainCore)

    @property
    def context_builder(self) -> Any:
        """Resolve the registered IContextBuilder (Phase 5.1)."""
        from brain.core.interfaces import IContextBuilder
        return self._container.resolve(IContextBuilder)

    @property
    def planner(self) -> Any:
        """Resolve the registered IPlanner (Phase 5.4 Step 8: PlannerChain)."""
        from brain.core.interfaces import IPlanner
        return self._container.resolve(IPlanner)

    @property
    def skill_registry(self) -> Any:
        """Resolve the registered SkillRegistry (Phase 5.2)."""
        from brain.skills.registry import SkillRegistry
        return self._container.resolve(SkillRegistry)

    @property
    def skill_manager(self) -> Any:
        """Resolve the registered SkillManager (Phase 5.2)."""
        from brain.skills.manager import SkillManager
        return self._container.resolve(SkillManager)

    @property
    def llm_planner(self) -> Any:
        """Resolve the registered LLMPlanner (Phase 5.3; inert until a
        model gateway is bound)."""
        from brain.planning.llm_planner import LLMPlanner
        return self._container.resolve(LLMPlanner)

    @property
    def planner_chain(self) -> Any:
        """Resolve the registered PlannerChain (Phase 5.3:
        RulePlanner -> LLMPlanner fallback)."""
        from brain.planning.llm_planner import PlannerChain
        return self._container.resolve(PlannerChain)

    @property
    def legacy_executor(self) -> Any:
        """Resolve the registered LegacyToolExecutor (Phase 5.4 Step 5).

        A session binds a dispatch closure into this instance at start and
        unbinds at stop (Step 6). Unbound (inert) until then."""
        from brain.skills.executors.legacy_tool_executor import LegacyToolExecutor
        return self._container.resolve(LegacyToolExecutor)

    # ---- Adapters ------------------------------------------------------

    @property
    def brain_state_adapter(self) -> BrainStateAdapter:
        return services.get_brain_state_adapter(self._container)

    @property
    def event_bus_adapter(self) -> EventBusAdapter:
        return services.get_event_bus_adapter(self._container)

    @property
    def pipeline_adapter(self) -> PipelineAdapter:
        return services.get_pipeline_adapter(self._container)

    def new_execution_context_adapter(self) -> ExecutionContextAdapter:
        """
        Resolve a fresh ExecutionContextAdapter (transient — one per call).

        Named as a method rather than a property to make the per-call
        construction explicit at the call site.
        """
        return services.get_execution_context_adapter(self._container)
