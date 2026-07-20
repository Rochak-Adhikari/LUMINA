"""
brain/skill_runtime/runtime_pipeline.py — Phase 8.11: Runtime Pipeline Orchestrator

The first component that understands the complete runtime chain. It coordinates
the already-existing stages in order and returns an immutable
RuntimePipelineResult:

    discovery → matching → resolution → sandbox → loader → context injection
      → executor → observer → recorder → persistence

Pure coordination ONLY. It contains NO business logic, duplicates nothing,
inspects no internals, mutates no output, and performs no retries, branching,
learning, memory, or storage. Each stage receives the previous stage's output;
on the first failure the orchestrator stops and propagates the reason, leaving
downstream fields None.

Stage services are constructor-injected (the stage interfaces) — no service
locator, no container access, no upward imports. Depends only on the
skill_runtime interfaces + models.
"""

from __future__ import annotations

from typing import Optional, Tuple

from brain.skill_runtime.interfaces import (
    ICapabilityMatcher,
    IContextInjector,
    IDependencyResolver,
    IExecutionObserver,
    IExecutionPersistence,
    IExecutionRecorder,
    IRegistryDiscovery,
    IRuntimePipeline,
    ISkillExecutor,
    ISkillLoader,
    ISkillSandbox,
)
from brain.skill_runtime.models import (
    CapabilityRequest,
    RuntimePipelineResult,
    SandboxPolicy,
)


class RuntimePipeline(IRuntimePipeline):
    """Coordinator over the ten runtime stages. Holds no business logic."""

    def __init__(
        self,
        discovery: IRegistryDiscovery,
        matcher: ICapabilityMatcher,
        resolver: IDependencyResolver,
        sandbox: ISkillSandbox,
        loader: ISkillLoader,
        injector: IContextInjector,
        executor: ISkillExecutor,
        observer: IExecutionObserver,
        recorder: IExecutionRecorder,
        persistence: IExecutionPersistence,
    ) -> None:
        self._discovery = discovery
        self._matcher = matcher
        self._resolver = resolver
        self._sandbox = sandbox
        self._loader = loader
        self._injector = injector
        self._executor = executor
        self._observer = observer
        self._recorder = recorder
        self._persistence = persistence

    def run(
        self,
        request: CapabilityRequest,
        *,
        policy: SandboxPolicy,
        query: str = "",
        granted_permissions: Optional[Tuple[str, ...]] = None,
        runtime_version: str = "",
        available_capabilities: Optional[Tuple[str, ...]] = None,
        conversation_id: str = "",
        user_input: str = "",
        memory_snapshot: Optional[dict] = None,
        workspace_snapshot: Optional[dict] = None,
        environment_snapshot: Optional[dict] = None,
        available_tools: Optional[Tuple[str, ...]] = None,
        variables: Optional[dict] = None,
        metadata: Optional[dict] = None,
        timestamp: Optional[str] = None,
        storage_key: str = "",
    ) -> RuntimePipelineResult:
        # 1. Discovery
        discovery = self._discovery.discover(query)
        if not discovery.skills:
            return RuntimePipelineResult(discovery=discovery, reason="discovery_empty")

        # 2. Matching
        match = self._matcher.match(request)
        if not match.matches:
            return RuntimePipelineResult(
                discovery=discovery, match=match, reason="no_match"
            )

        # 3. Resolution
        resolution = self._resolver.resolve(
            match,
            granted_permissions=granted_permissions,
            runtime_version=runtime_version,
            available_capabilities=available_capabilities,
        )
        if not resolution.resolved:
            return RuntimePipelineResult(
                discovery=discovery, match=match, resolution=resolution,
                reason="unresolved",
            )

        # 4. Sandbox
        sandbox = self._sandbox.evaluate(resolution, policy)
        if not sandbox.approved:
            return RuntimePipelineResult(
                discovery=discovery, match=match, resolution=resolution,
                sandbox=sandbox, reason="sandbox_denied",
            )

        registry_key = resolution.skill.registry_key if resolution.skill else ""

        # 5. Loader
        loaded = self._loader.load(sandbox)
        if not loaded.loaded:
            return RuntimePipelineResult(
                registry_key=registry_key, discovery=discovery, match=match,
                resolution=resolution, sandbox=sandbox, loaded=loaded,
                reason="load_failed",
            )

        # 6. Context Injection
        context = self._injector.inject(
            loaded,
            conversation_id=conversation_id,
            user_input=user_input,
            memory_snapshot=memory_snapshot,
            workspace_snapshot=workspace_snapshot,
            environment_snapshot=environment_snapshot,
            available_tools=available_tools,
            variables=variables,
            metadata=metadata,
        )
        if not context.prepared:
            return RuntimePipelineResult(
                registry_key=registry_key, discovery=discovery, match=match,
                resolution=resolution, sandbox=sandbox, loaded=loaded,
                context=context, reason="context_not_prepared",
            )

        # 7. Executor
        execution = self._executor.execute(loaded, context.context)
        if not execution.succeeded:
            observation = self._observer.observe(execution, timestamp=timestamp)
            record = self._recorder.record(
                observation, conversation_id=conversation_id,
                metadata=metadata, timestamp=timestamp,
            )
            persistence = self._persistence.prepare(record, storage_key=storage_key)
            return RuntimePipelineResult(
                registry_key=registry_key, discovery=discovery, match=match,
                resolution=resolution, sandbox=sandbox, loaded=loaded,
                context=context, execution=execution, observation=observation,
                record=record, persistence=persistence, reason="execution_failed",
            )

        # 8. Observer → 9. Recorder → 10. Persistence
        observation = self._observer.observe(execution, timestamp=timestamp)
        record = self._recorder.record(
            observation, conversation_id=conversation_id,
            metadata=metadata, timestamp=timestamp,
        )
        persistence = self._persistence.prepare(record, storage_key=storage_key)

        return RuntimePipelineResult(
            completed=True, registry_key=registry_key, discovery=discovery,
            match=match, resolution=resolution, sandbox=sandbox, loaded=loaded,
            context=context, execution=execution, observation=observation,
            record=record, persistence=persistence, reason="",
        )
