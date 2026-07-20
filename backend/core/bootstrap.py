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

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.application import ApplicationHost

from core.container import DependencyContainer
from core.interfaces import IBrainState, IEventBus, IPipeline, ISmartHomeAgent, IMemoryManager, IWorkspaceManager, IKnowledgeManager
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
    LIFECYCLE_SINGLETON,
)

# Phase 5.4 Order 4 (D2): tool-handler registration relocated here from
# core/__init__.py. Importing core.tool_handlers has the side effect of
# registering all Tier-1 handlers into ToolDispatcherRegistry (and pulls in
# the Gemini SDK). Doing it here — where the composition root already runs
# once at startup, before any tool dispatch — keeps the model SDK out of the
# core package spine while preserving Tier-1 tool registration exactly.
import core.tool_handlers  # noqa: F401 — side-effect: populates ToolDispatcherRegistry


class Bootstrapper:
    """
    Constructs core services and wires them into the container.

    kasa_agent is passed in already-constructed (or None) because its
    construction depends on settings resolved earlier in server.py's
    startup sequence — Bootstrapper only registers it, it does not decide
    whether it should exist.
    """

    def __init__(self, container: DependencyContainer, kasa_agent: Optional[Any] = None, app_host: Optional[ApplicationHost] = None) -> None:
        self._container = container
        self._kasa_agent = kasa_agent
        self._app_host = app_host  # Phase 4.5: ApplicationHost reference for registration
        self.brain_state: Optional[BrainState] = None
        self.event_bus: Optional[InProcessEventBus] = None
        self.memory_store: Optional[Any] = None
        self.project_manager: Optional[Any] = None
        self.memory_engine: Optional[Any] = None
        self.context_factory: Optional[ExecutionContextFactory] = None
        self.pipeline: Optional[RequestPipeline] = None
        self.brain_state_adapter: Optional[BrainStateAdapter] = None
        self.event_bus_adapter: Optional[EventBusAdapter] = None
        self.pipeline_adapter: Optional[PipelineAdapter] = None
        self.metadata_registry: Optional[ServiceMetadataRegistry] = None
        self.context_builder: Optional[Any] = None
        self.brain_core: Optional[Any] = None
        self.planner: Optional[Any] = None
        self.skill_registry: Optional[Any] = None
        self.skill_manager: Optional[Any] = None
        self.legacy_executor: Optional[Any] = None
        self.llm_planner: Optional[Any] = None
        self.planner_chain: Optional[Any] = None
        self.workspace_memory_store: Optional[Any] = None
        self.workspace_memory_manager: Optional[Any] = None
        self.workspace_sync: Optional[Any] = None
        self.reflection_engine: Optional[Any] = None

    def bootstrap(self) -> None:
        """Construct and register all services owned by this bootstrapper."""
        self._register_smart_home_agent()
        self._register_brain_state()
        self._register_event_bus()
        self._register_memory_store()
        self._register_project_manager()
        self._register_memory_engine()
        self._register_execution_context_factory()
        self._register_pipeline()
        self._register_adapters()
        self._register_planning_and_skills()
        self._register_workspace_memory()
        self._register_reflection()
        self._register_evolution()
        self._register_brain_core()
        self._register_service_metadata()

        # Phase 4.5: Register ApplicationHost as a singleton so it's accessible
        # through RuntimeFacade for unified lifecycle coordination
        if self._app_host is not None:
            self._container.register_instance(type(self._app_host), self._app_host)
            print("[DI] ApplicationHost registered")

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

    def _register_memory_store(self) -> None:
        import os
        from memory_store import MemoryStore
        
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        memory_db_path = os.path.join(backend_dir, "lumina_memory.db")
        
        self.memory_store = MemoryStore(memory_db_path)
        self._container.register_instance(IMemoryManager, self.memory_store)
        print("[DI] IMemoryManager -> MemoryStore registered")

    def _register_project_manager(self) -> None:
        import os
        from project_manager import ProjectManager

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(backend_dir)

        self.project_manager = ProjectManager(project_root)
        self._container.register_instance(IWorkspaceManager, self.project_manager)
        print("[DI] IWorkspaceManager -> ProjectManager registered")

    def _register_memory_engine(self) -> None:
        """
        Register MemoryEngine (IKnowledgeManager) as a LAZY singleton.

        Construction is deferred to first resolve because MemoryEngine's
        embedding provider probes the Gemini API at init — doing that at
        module import would slow startup and fail offline. MemoryStore is
        registered eagerly above, so all tables exist before the engine's
        first use (preserving the Phase E5 init-order requirement).
        """
        def _build_memory_engine():
            from memory_engine import MemoryEngine
            self.memory_engine = MemoryEngine(db_path=str(self.memory_store.db_path))
            return self.memory_engine

        self._container.register_singleton(IKnowledgeManager, _build_memory_engine)
        print("[DI] IKnowledgeManager -> MemoryEngine registered (lazy singleton)")

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

    def _register_brain_core(self) -> None:
        """
        Register the cognitive core — ContextBuilder and BrainCore.

        Phase 5.4 Step 4/5: BrainCore now receives the PlannerChain and
        SkillManager registered by _register_planning_and_skills() (which runs
        first). Orchestration stays DORMANT-SAFE: the LegacyToolExecutor is
        unbound until a session binds it (Step 6), so execution fails and
        handle() returns handled=False — identical to the prior skeleton
        contract. No runtime path resolves IBrainCore yet.

        Imported locally (like MemoryStore/ProjectManager above) to keep
        module import order flat.
        """
        from brain.core.interfaces import IBrainCore, IContextBuilder
        from brain.core.context_builder import ContextBuilder
        from brain.core.brain_core import BrainCore

        self.context_builder = ContextBuilder(
            brain_state=self.brain_state,
            workspace_memory_manager=self.workspace_memory_manager,
        )
        self._container.register_instance(IContextBuilder, self.context_builder)
        print("[DI] IContextBuilder -> ContextBuilder registered")

        self.brain_core = BrainCore(
            context_builder=self.context_builder,
            event_bus=self.event_bus,
            planner=self.planner_chain,
            skill_manager=self.skill_manager,
            reflection_engine=self.reflection_engine,
        )
        self._container.register_instance(IBrainCore, self.brain_core)
        print("[DI] IBrainCore -> BrainCore registered (planner+manager injected)")

    def _register_workspace_memory(self) -> None:
        """
        Phase 5.6.4: Register the workspace-memory store and manager.

        Dormant — no runtime path consumes them yet (ContextBuilder enrichment
        and switch wiring are later milestones). The manager coordinates the
        active WorkspaceMemory via the store; it holds no project files, no
        ProjectManager logic, and no Brain/Planner coupling. Local imports keep
        module import order flat (like MemoryStore/ProjectManager above).
        """
        from brain.workspace.store import WorkspaceMemoryStore
        from brain.workspace.manager import WorkspaceMemoryManager
        from brain.workspace.sync import WorkspaceSync

        self.workspace_memory_store = WorkspaceMemoryStore()
        self._container.register_instance(WorkspaceMemoryStore, self.workspace_memory_store)
        print("[DI] WorkspaceMemoryStore registered")

        self.workspace_memory_manager = WorkspaceMemoryManager(
            store=self.workspace_memory_store
        )
        self._container.register_instance(
            WorkspaceMemoryManager, self.workspace_memory_manager
        )
        print("[DI] WorkspaceMemoryManager registered (dormant)")

        # Phase 5.6.6: WorkspaceSync bridges ProjectManager → WorkspaceMemory.
        # Registered dormant — NOT wired into any runtime switch path yet.
        self.workspace_sync = WorkspaceSync(self.workspace_memory_manager)
        self._container.register_instance(WorkspaceSync, self.workspace_sync)
        print("[DI] WorkspaceSync registered (dormant)")

    def _register_reflection(self) -> None:
        """
        Phase 5.7.3: Register the ReflectionEngine (dormant).

        Pure, deterministic, read-only post-execution evaluator. Owns no
        runtime state. No consumer yet — BrainCore integration is a later
        milestone (5.7.4). Registered under both its interface and concrete
        type, mirroring the workspace-service registration style.
        """
        from brain.reflection.interfaces import IReflectionEngine
        from brain.reflection.engine import ReflectionEngine

        self.reflection_engine = ReflectionEngine()
        self._container.register_instance(IReflectionEngine, self.reflection_engine)
        self._container.register_instance(ReflectionEngine, self.reflection_engine)
        print("[DI] ReflectionEngine registered (dormant)")

    def _register_evolution(self) -> None:
        """
        Phase 6.1: Register the Evolution observation layer (dormant).

        EvolutionStore (append-only) + EvolutionObserver (Reflection →
        EvolutionObservation → store). ANALYSIS layer only (ADR-0008): observes
        and persists; never mutates runtime. No consumer yet — no runtime path
        invokes the observer. Registered under interface + concrete type,
        mirroring the reflection/workspace registration style.
        """
        from brain.evolution.interfaces import IEvolutionStore, IEvolutionObserver
        from brain.evolution.store import EvolutionStore
        from brain.evolution.observer import EvolutionObserver

        self.evolution_store = EvolutionStore()
        self.evolution_observer = EvolutionObserver(self.evolution_store)
        self._container.register_instance(IEvolutionStore, self.evolution_store)
        self._container.register_instance(EvolutionStore, self.evolution_store)
        self._container.register_instance(IEvolutionObserver, self.evolution_observer)
        self._container.register_instance(EvolutionObserver, self.evolution_observer)
        print("[DI] EvolutionObserver registered (dormant)")

        # Phase 6.2: StrategyEvaluator — deterministic analysis over stored
        # observations. Reads EvolutionStore only; never Reflection. Dormant.
        from brain.evolution.interfaces import IStrategyEvaluator
        from brain.evolution.evaluator import StrategyEvaluator

        self.strategy_evaluator = StrategyEvaluator(self.evolution_store)
        self._container.register_instance(IStrategyEvaluator, self.strategy_evaluator)
        self._container.register_instance(StrategyEvaluator, self.strategy_evaluator)
        print("[DI] StrategyEvaluator registered (dormant)")

        # Phase 6.3: PerformanceAnalyzer — deterministic measurement over a
        # StrategyAnalysis. Consumes StrategyAnalysis only; never Reflection,
        # observations, or the store. Stateless. Dormant.
        from brain.evolution.interfaces import IPerformanceAnalyzer
        from brain.evolution.analyzer import PerformanceAnalyzer

        self.performance_analyzer = PerformanceAnalyzer()
        self._container.register_instance(IPerformanceAnalyzer, self.performance_analyzer)
        self._container.register_instance(PerformanceAnalyzer, self.performance_analyzer)
        print("[DI] PerformanceAnalyzer registered (dormant)")

        # Phase 6.4: MemoryConsolidator — read-only consolidation proposer over
        # a memory snapshot. Never writes memory; descriptive proposals only.
        # Stateless. Dormant.
        from brain.evolution.interfaces import IMemoryConsolidator
        from brain.evolution.consolidator import MemoryConsolidator

        self.memory_consolidator = MemoryConsolidator()
        self._container.register_instance(IMemoryConsolidator, self.memory_consolidator)
        self._container.register_instance(MemoryConsolidator, self.memory_consolidator)
        print("[DI] MemoryConsolidator registered (dormant)")

        # Phase 6.5: RecommendationEngine (Self Evolution) — decides WHAT should
        # evolve. Consumes PerformanceAnalysis + ConsolidationProposalSet only;
        # never performs evolution. Stateless. Dormant.
        from brain.evolution.interfaces import IRecommendationEngine
        from brain.evolution.recommender import RecommendationEngine

        self.recommendation_engine = RecommendationEngine()
        self._container.register_instance(IRecommendationEngine, self.recommendation_engine)
        self._container.register_instance(RecommendationEngine, self.recommendation_engine)
        print("[DI] RecommendationEngine registered (dormant)")

        self._register_skill_creator()
        self._register_skill_runtime()

    def _register_skill_runtime(self) -> None:
        """
        Phase 8.1: Registry Discovery — the first runtime consumer of the frozen
        Phase 7 registry. Read-only; answers "what skills exist?" by projecting
        RegistryEntry into DiscoveredSkill. No runtime path wires into it yet
        (dormant); registered here so the Planner can later resolve it via DI
        instead of importing skills directly.
        """
        from brain.skill_runtime.interfaces import IRegistryDiscovery
        from brain.skill_runtime.registry_discovery import RegistryDiscovery

        self.registry_discovery = RegistryDiscovery(self.blueprint_registry)
        self._container.register_instance(IRegistryDiscovery, self.registry_discovery)
        self._container.register_instance(RegistryDiscovery, self.registry_discovery)
        print("[DI] RegistryDiscovery registered (dormant)")

        self._register_capability_matcher()

    def _register_capability_matcher(self) -> None:
        """
        Phase 8.2: Capability Matching — semantic layer over Registry Discovery.
        Answers "which skills satisfy this capability?" Depends only on
        IRegistryDiscovery; pure and deterministic. Dormant — no runtime path
        wires into it yet.
        """
        from brain.skill_runtime.interfaces import ICapabilityMatcher
        from brain.skill_runtime.capability_matcher import CapabilityMatcher

        self.capability_matcher = CapabilityMatcher(self.registry_discovery)
        self._container.register_instance(ICapabilityMatcher, self.capability_matcher)
        self._container.register_instance(CapabilityMatcher, self.capability_matcher)
        print("[DI] CapabilityMatcher registered (dormant)")

        self._register_dependency_resolver()

    def _register_dependency_resolver(self) -> None:
        """
        Phase 8.3: Dependency Resolution — the gate between matching and loading.
        Selects the top-ranked match whose dependencies are satisfied. Depends
        only on Phase 8.2 output + supplied grants; pure and deterministic.
        Dormant — no runtime path wires into it yet.
        """
        from brain.skill_runtime.interfaces import IDependencyResolver
        from brain.skill_runtime.dependency_resolver import DependencyResolver

        self.dependency_resolver = DependencyResolver()
        self._container.register_instance(IDependencyResolver, self.dependency_resolver)
        self._container.register_instance(DependencyResolver, self.dependency_resolver)
        print("[DI] DependencyResolver registered (dormant)")

        self._register_skill_sandbox()

    def _register_skill_sandbox(self) -> None:
        """
        Phase 8.4: Skill Sandbox — first runtime execution-safety layer. Pure
        allow/deny gatekeeper over a DependencyResolution + SandboxPolicy. Never
        loads or executes. Depends only on Phase 8.3 output. Dormant.
        """
        from brain.skill_runtime.interfaces import ISkillSandbox
        from brain.skill_runtime.skill_sandbox import SkillSandbox

        self.skill_sandbox = SkillSandbox()
        self._container.register_instance(ISkillSandbox, self.skill_sandbox)
        self._container.register_instance(SkillSandbox, self.skill_sandbox)
        print("[DI] SkillSandbox registered (dormant)")

        self._register_skill_loader()

    def _register_skill_loader(self) -> None:
        """
        Phase 8.5: Skill Loader — turns an approved SandboxDecision into a loaded,
        validated skill instance (import + instantiate + interface check). Never
        executes. Depends only on Phase 8.4 output. Dormant.
        """
        from brain.skill_runtime.interfaces import ISkillLoader
        from brain.skill_runtime.skill_loader import SkillLoader

        self.skill_loader = SkillLoader()
        self._container.register_instance(ISkillLoader, self.skill_loader)
        self._container.register_instance(SkillLoader, self.skill_loader)
        print("[DI] SkillLoader registered (dormant)")

        self._register_skill_executor()

    def _register_skill_executor(self) -> None:
        """
        Phase 8.6: Skill Executor — runs a LoadedSkill exactly once via its
        canonical run(context). Never retries/recovers/chains; converts failures
        into structured ExecutionResult. Depends only on Phase 8.5 output. Dormant.
        """
        from brain.skill_runtime.interfaces import ISkillExecutor
        from brain.skill_runtime.skill_executor import SkillExecutor

        self.skill_executor = SkillExecutor()
        self._container.register_instance(ISkillExecutor, self.skill_executor)
        self._container.register_instance(SkillExecutor, self.skill_executor)
        print("[DI] SkillExecutor registered (dormant)")

        self._register_context_injector()

    def _register_context_injector(self) -> None:
        """
        Phase 8.7: Context Injection — pure builder of an immutable
        ExecutionContext from a LoadedSkill + caller data. Never loads/executes/
        accesses services. Depends only on Phase 8.5 output. Dormant.
        """
        from brain.skill_runtime.interfaces import IContextInjector
        from brain.skill_runtime.context_injector import ContextInjector

        self.context_injector = ContextInjector()
        self._container.register_instance(IContextInjector, self.context_injector)
        self._container.register_instance(ContextInjector, self.context_injector)
        print("[DI] ContextInjector registered (dormant)")

        self._register_execution_observer()

    def _register_execution_observer(self) -> None:
        """
        Phase 8.8: Execution Observer — purely observational. Converts an
        ExecutionResult into an immutable ExecutionObservation. Never executes,
        retries, or mutates. Depends only on ExecutionResult. Dormant.
        """
        from brain.skill_runtime.interfaces import IExecutionObserver
        from brain.skill_runtime.execution_observer import ExecutionObserver

        self.execution_observer = ExecutionObserver()
        self._container.register_instance(IExecutionObserver, self.execution_observer)
        self._container.register_instance(ExecutionObserver, self.execution_observer)
        print("[DI] ExecutionObserver registered (dormant)")

        self._register_execution_recorder()

    def _register_execution_recorder(self) -> None:
        """
        Phase 8.9: Execution Recorder — pure transformation of an
        ExecutionObservation into a persistence-ready ExecutionRecord. Does NOT
        persist/log/save. Depends only on the observation. Dormant.
        """
        from brain.skill_runtime.interfaces import IExecutionRecorder
        from brain.skill_runtime.execution_recorder import ExecutionRecorder

        self.execution_recorder = ExecutionRecorder()
        self._container.register_instance(IExecutionRecorder, self.execution_recorder)
        self._container.register_instance(ExecutionRecorder, self.execution_recorder)
        print("[DI] ExecutionRecorder registered (dormant)")

        self._register_execution_persistence()

    def _register_execution_persistence(self) -> None:
        """
        Phase 8.10: Execution Persistence — prepare step (NOT storage). Wraps an
        ExecutionRecord into a PersistenceResult; stores nothing. Depends only on
        the record. Dormant.
        """
        from brain.skill_runtime.interfaces import IExecutionPersistence
        from brain.skill_runtime.execution_persistence import ExecutionPersistence

        self.execution_persistence = ExecutionPersistence()
        self._container.register_instance(IExecutionPersistence, self.execution_persistence)
        self._container.register_instance(ExecutionPersistence, self.execution_persistence)
        print("[DI] ExecutionPersistence registered (dormant)")

        self._register_runtime_pipeline()

    def _register_runtime_pipeline(self) -> None:
        """
        Phase 8.11: Runtime Pipeline Orchestrator — coordinates the ten runtime
        stages in order (discovery → … → persistence) into a RuntimePipelineResult.
        Pure coordination, no business logic; stages constructor-injected. Dormant.
        """
        from brain.skill_runtime.interfaces import IRuntimePipeline
        from brain.skill_runtime.runtime_pipeline import RuntimePipeline

        self.runtime_pipeline = RuntimePipeline(
            self.registry_discovery,
            self.capability_matcher,
            self.dependency_resolver,
            self.skill_sandbox,
            self.skill_loader,
            self.context_injector,
            self.skill_executor,
            self.execution_observer,
            self.execution_recorder,
            self.execution_persistence,
        )
        self._container.register_instance(IRuntimePipeline, self.runtime_pipeline)
        self._container.register_instance(RuntimePipeline, self.runtime_pipeline)
        print("[DI] RuntimePipeline registered (dormant)")

        self._register_failure_recovery()

    def _register_failure_recovery(self) -> None:
        """
        Phase 8.12: Failure Recovery — descriptive advisor over a
        RuntimePipelineResult, producing a RecoveryPlan. Names WHAT recovery
        should happen; acts on nothing. Pure/deterministic. Dormant.
        """
        from brain.skill_runtime.interfaces import IFailureRecovery
        from brain.skill_runtime.failure_recovery import FailureRecovery

        self.failure_recovery = FailureRecovery()
        self._container.register_instance(IFailureRecovery, self.failure_recovery)
        self._container.register_instance(FailureRecovery, self.failure_recovery)
        print("[DI] FailureRecovery registered (dormant)")

        self._register_runtime_validator()

    def _register_runtime_validator(self) -> None:
        """
        Phase 8.13: Runtime Validation — read-only integrity checker over a
        RuntimePipelineResult, producing a ValidationReport. Asserts structural
        consistency; repairs/mutates nothing. Pure/deterministic. Dormant.
        """
        from brain.skill_runtime.interfaces import IRuntimeValidator
        from brain.skill_runtime.runtime_validation import RuntimeValidator

        self.runtime_validator = RuntimeValidator()
        self._container.register_instance(IRuntimeValidator, self.runtime_validator)
        self._container.register_instance(RuntimeValidator, self.runtime_validator)
        print("[DI] RuntimeValidator registered (dormant)")

    def _register_skill_creator(self) -> None:
        """
        Phase 7.2: Register the Skill Creator (dormant).

        BlueprintBuilder is the concrete ISkillCreator: a deterministic
        transformer of EvolutionRecommendationSet → SkillBlueprintSet (metadata
        only). It generates no code, installs nothing, touches no runtime. No
        runtime path consumes it — registration only. Boot byte-identical.
        """
        from brain.skill_creator.interfaces import ISkillCreator
        from brain.skill_creator.blueprint_builder import BlueprintBuilder

        self.blueprint_builder = BlueprintBuilder()
        self._container.register_instance(ISkillCreator, self.blueprint_builder)
        self._container.register_instance(BlueprintBuilder, self.blueprint_builder)
        print("[DI] BlueprintBuilder registered (dormant)")

        # Phase 7.3: BlueprintVerifier (pipeline stage 02) — deterministic
        # static verification of a SkillBlueprint. No runtime consumer yet.
        from brain.skill_creator.interfaces import IBlueprintVerifier
        from brain.skill_creator.blueprint_verifier import BlueprintVerifier

        self.blueprint_verifier = BlueprintVerifier()
        self._container.register_instance(IBlueprintVerifier, self.blueprint_verifier)
        self._container.register_instance(BlueprintVerifier, self.blueprint_verifier)
        print("[DI] BlueprintVerifier registered (dormant)")

        # Phase 7.4: BlueprintGenerator (pipeline stage 03) — deterministic
        # package descriptor generation from a verified blueprint. Gated on
        # verification; no filesystem, no execution. No runtime consumer yet.
        from brain.skill_creator.interfaces import IBlueprintGenerator
        from brain.skill_creator.blueprint_generator import BlueprintGenerator

        self.blueprint_generator = BlueprintGenerator()
        self._container.register_instance(IBlueprintGenerator, self.blueprint_generator)
        self._container.register_instance(BlueprintGenerator, self.blueprint_generator)
        print("[DI] BlueprintGenerator registered (dormant)")

        # Phase 7.5: BlueprintTester (pipeline stage 04) — deterministic static
        # testing of a generated package. Gated on generation; no execution, no
        # filesystem. No runtime consumer yet.
        from brain.skill_creator.interfaces import IBlueprintTester
        from brain.skill_creator.blueprint_tester import BlueprintTester

        self.blueprint_tester = BlueprintTester()
        self._container.register_instance(IBlueprintTester, self.blueprint_tester)
        self._container.register_instance(BlueprintTester, self.blueprint_tester)
        print("[DI] BlueprintTester registered (dormant)")

        # Phase 7.6: BlueprintApprover (pipeline stage 05) — mandatory human
        # gate. Records an explicit human decision over a TestResult; never
        # auto-approves. Deterministic, no side effects. No runtime consumer yet.
        from brain.skill_creator.interfaces import IBlueprintApprover
        from brain.skill_creator.blueprint_approver import BlueprintApprover

        self.blueprint_approver = BlueprintApprover()
        self._container.register_instance(IBlueprintApprover, self.blueprint_approver)
        self._container.register_instance(BlueprintApprover, self.blueprint_approver)
        print("[DI] BlueprintApprover registered (dormant)")

        # Phase 7.7: BlueprintInstaller (pipeline stage 06) — materializes an
        # approved generated package to disk. Gated on approval; idempotent;
        # never executes/activates/registers. No runtime consumer yet.
        from brain.skill_creator.interfaces import IBlueprintInstaller
        from brain.skill_creator.blueprint_installer import BlueprintInstaller

        self.blueprint_installer = BlueprintInstaller()
        self._container.register_instance(IBlueprintInstaller, self.blueprint_installer)
        self._container.register_instance(BlueprintInstaller, self.blueprint_installer)
        print("[DI] BlueprintInstaller registered (dormant)")

        # Phase 7.8: BlueprintRegistry (pipeline stage 07) — append-only catalog
        # of installed skills. Gated on installation; never overwrites entries.
        # No runtime consumer yet.
        from brain.skill_creator.interfaces import IBlueprintRegistry
        from brain.skill_creator.blueprint_registry import BlueprintRegistry

        self.blueprint_registry = BlueprintRegistry()
        self._container.register_instance(IBlueprintRegistry, self.blueprint_registry)
        self._container.register_instance(BlueprintRegistry, self.blueprint_registry)
        print("[DI] BlueprintRegistry registered (dormant)")

        # Phase 7.9: LifecycleManager (pipeline stage 08) — append-only lifecycle
        # event log over registered skills. Never edits registry/prior events.
        # No runtime consumer yet.
        from brain.skill_creator.interfaces import ILifecycleManager
        from brain.skill_creator.lifecycle_manager import LifecycleManager

        self.lifecycle_manager = LifecycleManager()
        self._container.register_instance(ILifecycleManager, self.lifecycle_manager)
        self._container.register_instance(LifecycleManager, self.lifecycle_manager)
        print("[DI] LifecycleManager registered (dormant)")

        # Phase 7.10: MarketplacePublisher (pipeline stage 09) — deterministic
        # marketplace manifest construction. No networking, no I/O, no mutation.
        # No runtime consumer yet.
        from brain.skill_creator.interfaces import IMarketplacePublisher
        from brain.skill_creator.marketplace_publisher import MarketplacePublisher

        self.marketplace_publisher = MarketplacePublisher()
        self._container.register_instance(IMarketplacePublisher, self.marketplace_publisher)
        self._container.register_instance(MarketplacePublisher, self.marketplace_publisher)
        print("[DI] MarketplacePublisher registered (dormant)")

        # Phase 7.11: RollbackManager (pipeline stage 10, final) — reverses the
        # installer's filesystem materialization. Deterministic, idempotent;
        # deletes only installer-created files. No runtime consumer yet.
        from brain.skill_creator.interfaces import IRollbackManager
        from brain.skill_creator.rollback_manager import RollbackManager

        self.rollback_manager = RollbackManager()
        self._container.register_instance(IRollbackManager, self.rollback_manager)
        self._container.register_instance(RollbackManager, self.rollback_manager)
        print("[DI] RollbackManager registered (dormant)")

    def _register_planning_and_skills(self) -> None:
        """
        Phase 5.2: Register the deterministic planning + skill layer.

        - IPlanner        -> RulePlanner (deterministic, no AI)
        - SkillRegistry   -> metadata registry seeded with builtin specs
        - SkillManager    -> dispatch with an UNBOUND LegacyToolExecutor
                             (no runtime wiring in 5.2 — execution is inert)

        Local imports, no runtime consumers, no metadata records (keeps the
        Phase 1.8 registry count stable).
        """
        from brain.core.interfaces import IPlanner
        from brain.planning.rule_planner import RulePlanner
        from brain.skills.registry import SkillRegistry
        from brain.skills.manager import SkillManager
        from brain.skills.executors.legacy_tool_executor import LegacyToolExecutor
        from brain.skills.builtin import seed_registry

        self.planner = RulePlanner()
        print("[DI] RulePlanner constructed (chain member)")

        self.skill_registry = SkillRegistry()
        seeded = seed_registry(self.skill_registry)
        self._container.register_instance(SkillRegistry, self.skill_registry)
        print(f"[DI] SkillRegistry registered ({seeded} builtin skills seeded)")

        # Phase 5.4 Step 5: keep a reference to the executor and register it so
        # RuntimeFacade can expose it. A session binds a dispatch closure into
        # this instance at start (Step 6); it is unbound (inert) until then.
        self.legacy_executor = LegacyToolExecutor(dispatch=None)
        self._container.register_instance(LegacyToolExecutor, self.legacy_executor)
        print("[DI] LegacyToolExecutor registered (unbound)")

        self.skill_manager = SkillManager(
            registry=self.skill_registry,
            executors=[self.legacy_executor],
        )
        self._container.register_instance(SkillManager, self.skill_manager)
        print("[DI] SkillManager registered (legacy executor unbound)")

        # Phase 5.3: LLMPlanner + fallback chain. No IModelGateway
        # implementation exists in the repository, so the LLM planner is
        # registered UNBOUND (inert — plan() returns None). Phase 5.4 Step 8
        # binds IPlanner to the chain (below), retiring the earlier temporary
        # IPlanner -> RulePlanner compat binding.
        from brain.planning.llm_planner import LLMPlanner, PlannerChain

        self.llm_planner = LLMPlanner(
            model_gateway=None,
            skill_registry=self.skill_registry,
        )
        self._container.register_instance(LLMPlanner, self.llm_planner)
        print("[DI] LLMPlanner registered (model gateway unbound)")

        self.planner_chain = PlannerChain([self.planner, self.llm_planner])
        self._container.register_instance(PlannerChain, self.planner_chain)

        # Phase 5.4 Step 8: flip the IPlanner binding to the production planner.
        # The temporary IPlanner -> RulePlanner compat binding is retired now
        # that PlannerChain is validated end-to-end (Step 7). BrainCore already
        # receives the chain via direct injection; this aligns the interface
        # key with the production planner for any IPlanner consumer.
        self._container.register_instance(IPlanner, self.planner_chain)
        print("[DI] IPlanner -> PlannerChain registered (RulePlanner -> LLMPlanner)")
        print("[DI] PlannerChain registered (RulePlanner -> LLMPlanner)")

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
                name="MemoryStore", key=repr(IMemoryManager),
                lifecycle=LIFECYCLE_INSTANCE, owner="Phase 4.2",
                description="Passive memory persistence layer.",
            ),
            ServiceMetadata(
                name="ProjectManager", key=repr(IWorkspaceManager),
                lifecycle=LIFECYCLE_INSTANCE, owner="Phase 4.2",
                description="Project workspace manager.",
            ),
            ServiceMetadata(
                name="MemoryEngine", key=repr(IKnowledgeManager),
                lifecycle=LIFECYCLE_SINGLETON, owner="Phase 4.4",
                description="Semantic memory engine (lazy — built on first resolve).",
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
