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

    @property
    def workspace_memory_manager(self) -> Any:
        """Resolve the registered WorkspaceMemoryManager (Phase 5.6.4).

        Dormant — no runtime path consumes it yet."""
        from brain.workspace.manager import WorkspaceMemoryManager
        return self._container.resolve(WorkspaceMemoryManager)

    @property
    def workspace_sync(self) -> Any:
        """Resolve the registered WorkspaceSync coordinator (Phase 5.6.6).

        Dormant — bridges ProjectManager → WorkspaceMemory but is not wired
        into any runtime switch path yet."""
        from brain.workspace.sync import WorkspaceSync
        return self._container.resolve(WorkspaceSync)

    @property
    def reflection_engine(self) -> Any:
        """Resolve the registered ReflectionEngine (Phase 5.7.3).

        Dormant — a pure read-only post-execution evaluator; no runtime path
        consumes it yet (BrainCore integration is a later milestone)."""
        from brain.reflection.engine import ReflectionEngine
        return self._container.resolve(ReflectionEngine)

    @property
    def registry_discovery(self) -> Any:
        """Resolve the registered RegistryDiscovery (Phase 8.1).

        Read-only discovery over the installed-skill registry. Dormant — no
        runtime path consumes it yet."""
        from brain.skill_runtime.registry_discovery import RegistryDiscovery
        return self._container.resolve(RegistryDiscovery)

    @property
    def capability_matcher(self) -> Any:
        """Resolve the registered CapabilityMatcher (Phase 8.2).

        Semantic capability matching over discovered skills. Dormant — no
        runtime path consumes it yet."""
        from brain.skill_runtime.capability_matcher import CapabilityMatcher
        return self._container.resolve(CapabilityMatcher)

    @property
    def dependency_resolver(self) -> Any:
        """Resolve the registered DependencyResolver (Phase 8.3).

        Deterministic dependency gate over matched skills. Dormant — no runtime
        path consumes it yet."""
        from brain.skill_runtime.dependency_resolver import DependencyResolver
        return self._container.resolve(DependencyResolver)

    @property
    def skill_sandbox(self) -> Any:
        """Resolve the registered SkillSandbox (Phase 8.4).

        Pure runtime safety gatekeeper. Dormant — no runtime path consumes it
        yet."""
        from brain.skill_runtime.skill_sandbox import SkillSandbox
        return self._container.resolve(SkillSandbox)

    @property
    def skill_loader(self) -> Any:
        """Resolve the registered SkillLoader (Phase 8.5).

        Turns an approved skill into a loaded instance (import + instantiate +
        validate). Never executes. Dormant — no runtime path consumes it yet."""
        from brain.skill_runtime.skill_loader import SkillLoader
        return self._container.resolve(SkillLoader)

    @property
    def skill_executor(self) -> Any:
        """Resolve the registered SkillExecutor (Phase 8.6).

        Runs a loaded skill once via its canonical run(context). Dormant — no
        runtime path consumes it yet."""
        from brain.skill_runtime.skill_executor import SkillExecutor
        return self._container.resolve(SkillExecutor)

    @property
    def context_injector(self) -> Any:
        """Resolve the registered ContextInjector (Phase 8.7).

        Pure builder of an immutable ExecutionContext. Dormant — no runtime path
        consumes it yet."""
        from brain.skill_runtime.context_injector import ContextInjector
        return self._container.resolve(ContextInjector)

    @property
    def execution_observer(self) -> Any:
        """Resolve the registered ExecutionObserver (Phase 8.8).

        Purely observational — ExecutionResult → ExecutionObservation. Dormant —
        no runtime path consumes it yet."""
        from brain.skill_runtime.execution_observer import ExecutionObserver
        return self._container.resolve(ExecutionObserver)

    @property
    def execution_recorder(self) -> Any:
        """Resolve the registered ExecutionRecorder (Phase 8.9).

        Pure ExecutionObservation → ExecutionRecord (no persistence). Dormant —
        no runtime path consumes it yet."""
        from brain.skill_runtime.execution_recorder import ExecutionRecorder
        return self._container.resolve(ExecutionRecorder)

    @property
    def execution_persistence(self) -> Any:
        """Resolve the registered ExecutionPersistence (Phase 8.10).

        Prepare step for persistence (stores nothing) — ExecutionRecord →
        PersistenceResult. Dormant — no runtime path consumes it yet."""
        from brain.skill_runtime.execution_persistence import ExecutionPersistence
        return self._container.resolve(ExecutionPersistence)

    @property
    def runtime_pipeline(self) -> Any:
        """Resolve the registered RuntimePipeline (Phase 8.11).

        Coordinates the ten runtime stages (discovery → … → persistence) into a
        RuntimePipelineResult. Pure coordinator, no business logic. Dormant — no
        runtime path consumes it yet."""
        from brain.skill_runtime.runtime_pipeline import RuntimePipeline
        return self._container.resolve(RuntimePipeline)

    @property
    def failure_recovery(self) -> Any:
        """Resolve the registered FailureRecovery (Phase 8.12).

        Descriptive recovery advisor — RuntimePipelineResult → RecoveryPlan.
        Names WHAT recovery should happen; acts on nothing. Dormant — no runtime
        path consumes it yet."""
        from brain.skill_runtime.failure_recovery import FailureRecovery
        return self._container.resolve(FailureRecovery)

    @property
    def runtime_validator(self) -> Any:
        """Resolve the registered RuntimeValidator (Phase 8.13).

        Read-only integrity checker — RuntimePipelineResult → ValidationReport.
        Asserts structural consistency; repairs/mutates nothing. Dormant — no
        runtime path consumes it yet."""
        from brain.skill_runtime.runtime_validation import RuntimeValidator
        return self._container.resolve(RuntimeValidator)

    # ---- Phase 5.8.2: Workspace Activation ------------------------------

    def activate_workspace(self, project_manager: Any) -> Any:
        """Runtime entry point for Workspace Activation (Phase 5.8.2).

        Follows ProjectManager's active project into WorkspaceMemory by
        delegating to the WorkspaceSync coordinator. This is the single
        runtime abstraction for activation: callers invoke the facade, never
        WorkspaceSync directly, leaving room for future activation logic
        without touching call-sites.

        Idempotent: activating the already-active workspace is a no-op
        (WorkspaceSync short-circuits on unchanged path). Returns the current
        WorkspaceMemory.
        """
        return self.workspace_sync.sync_to(project_manager)

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
