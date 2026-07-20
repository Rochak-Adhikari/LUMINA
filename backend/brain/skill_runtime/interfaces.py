"""
brain/skill_runtime/interfaces.py — Phase 8.1: Registry Discovery contract

Behaviour-only contract for runtime skill discovery. Read-only: discovery
observes the registry and never registers, installs, mutates, or executes.
This is the abstraction the Planner asks "what skills exist?" through, so it
never imports skills (or the Registry) directly.

Imports only stdlib/abc + skill_runtime models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Tuple

from brain.skill_runtime.models import (
    CapabilityMatchResult,
    CapabilityRequest,
    ContextInjectionResult,
    DependencyResolution,
    ExecutionObservation,
    ExecutionRecord,
    ExecutionResult,
    LoadedSkill,
    PersistenceResult,
    RecoveryPlan,
    RegistrySearchResult,
    RuntimePipelineResult,
    SandboxDecision,
    SandboxPolicy,
    ValidationReport,
)


class IRegistryDiscovery(ABC):
    """Read-only discovery over the installed-skill registry (Phase 8.1)."""

    @abstractmethod
    def discover(self, query: str = "") -> RegistrySearchResult:
        """
        Return the registered skills matching ``query``.

        An empty query lists every registered skill. Matching is a deterministic
        case-insensitive substring test over skill_family / package_name /
        semantic_fingerprint. Only skills whose registration_status is
        "registered" are ever returned (skipped/unregistered entries are hidden).
        The result ordering is deterministic and independent of registry
        insertion order.
        """
        raise NotImplementedError


class ICapabilityMatcher(ABC):
    """
    Semantic capability matching over discovered skills (Phase 8.2).

    Where IRegistryDiscovery is descriptive ("what skills exist?"), this contract
    is semantic ("which skills satisfy this capability request?"). It depends
    ONLY on IRegistryDiscovery — never on the Registry, RegistryEntry, or any
    skill_creator stage — so the Planner asks the matcher and stays independent
    of the registry implementation.

    Pure and deterministic: no loading, no execution, no I/O, no importing skills,
    no registry mutation.
    """

    @abstractmethod
    def match(self, request: CapabilityRequest) -> CapabilityMatchResult:
        """
        Return the candidate skills that satisfy ``request``, ranked
        deterministically (score descending, then skill_family / package_name /
        registry_key). An unsatisfiable request yields an empty result.
        """
        raise NotImplementedError


class IDependencyResolver(ABC):
    """
    Dependency resolution over matched skills (Phase 8.3).

    Given a CapabilityMatchResult and the runtime's supplied grants (permissions,
    runtime version, provided capabilities), selects the top-ranked candidate
    whose requirements are all satisfied and returns a DependencyResolution.
    Nothing loads or executes until resolution succeeds.

    Depends only on Phase 8.2 output (CapabilityMatchResult) + supplied grants —
    never the Registry, RegistryEntry, or skill_creator. Pure and deterministic:
    no loading, execution, I/O, or mutation.
    """

    @abstractmethod
    def resolve(
        self,
        matches: CapabilityMatchResult,
        *,
        granted_permissions: Optional[Tuple[str, ...]] = None,
        runtime_version: str = "",
        available_capabilities: Optional[Tuple[str, ...]] = None,
    ) -> DependencyResolution:
        """
        Select the highest-ranked match whose dependencies are all satisfied and
        return an immutable DependencyResolution. If no candidate qualifies,
        ``resolved`` is False and ``skill`` is None.
        """
        raise NotImplementedError


class ISkillSandbox(ABC):
    """
    Runtime safety gatekeeper (Phase 8.4) — the first execution-safety layer.

    Given a DependencyResolution and a SandboxPolicy, decides whether the
    resolved skill MAY execute. It is PURELY a validator: it never loads,
    imports, or executes skills. Depends only on Phase 8.3 output +
    supplied policy. Pure and deterministic.
    """

    @abstractmethod
    def evaluate(
        self, resolution: DependencyResolution, policy: "SandboxPolicy"
    ) -> "SandboxDecision":
        """Return an allow/deny SandboxDecision for the resolved skill."""
        raise NotImplementedError


class ISkillLoader(ABC):
    """
    Skill loader (Phase 8.5) — turns an approved skill into a loaded instance.

    Given a SandboxDecision, verifies approval, locates the installed skill
    module, imports it, instantiates the ``Skill`` class, validates the required
    execute/run interface, and returns an immutable LoadedSkill. It NEVER
    executes the skill (that is Phase 8.6). Depends only on Phase 8.4 output.
    """

    @abstractmethod
    def load(self, decision: "SandboxDecision") -> "LoadedSkill":
        """Load the approved skill; return an immutable LoadedSkill."""
        raise NotImplementedError


class ISkillExecutor(ABC):
    """
    Skill executor (Phase 8.6) — runs a loaded skill exactly once.

    Given a LoadedSkill, calls its canonical ``run(context)`` entrypoint a single
    time and captures the outcome as an immutable ExecutionResult. Never retries,
    recovers, chains, plans, loads, or sandboxes. NEVER lets an exception
    propagate — failures become structured ExecutionResult. Depends only on
    Phase 8.5 output.
    """

    @abstractmethod
    def execute(self, loaded: "LoadedSkill", context: object = None) -> "ExecutionResult":
        """Run the loaded skill once; return an immutable ExecutionResult."""
        raise NotImplementedError


class IContextInjector(ABC):
    """
    Context injection (Phase 8.7) — prepares everything a skill needs to run.

    Given a LoadedSkill and caller-supplied data, builds an immutable
    ExecutionContext and returns a ContextInjectionResult. Pure transformation:
    never loads, executes, retries, recovers, chains, schedules, accesses the
    registry, imports skill_creator, plans, writes memory, or runs tools. Depends
    only on LoadedSkill + caller data + skill_runtime models.
    """

    @abstractmethod
    def inject(
        self,
        loaded: "LoadedSkill",
        *,
        conversation_id: str = "",
        user_input: str = "",
        memory_snapshot: Optional[dict] = None,
        workspace_snapshot: Optional[dict] = None,
        environment_snapshot: Optional[dict] = None,
        available_tools: Optional[Tuple[str, ...]] = None,
        variables: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> "ContextInjectionResult":
        """Build an immutable ExecutionContext for the loaded skill."""
        raise NotImplementedError


class IExecutionObserver(ABC):
    """
    Execution observer (Phase 8.8) — purely observational.

    Converts an immutable ExecutionResult into an immutable ExecutionObservation
    recording descriptive metadata for later systems. Never executes, retries,
    modifies output/memory, logs externally, touches disk, or calls services.
    Depends only on the ExecutionResult. Deterministic (timestamp is caller-
    supplied, never generated).
    """

    @abstractmethod
    def observe(
        self, result: "ExecutionResult", *, timestamp: Optional[str] = None
    ) -> "ExecutionObservation":
        """Return an immutable ExecutionObservation for *result*."""
        raise NotImplementedError


class IExecutionRecorder(ABC):
    """
    Execution recorder (Phase 8.9) — pure transformation, no persistence.

    Converts one immutable ExecutionObservation into one immutable
    ExecutionRecord ready for later persistence. Never executes, persists, logs,
    saves, learns, updates memory, or mutates the observation. Depends only on
    the ExecutionObservation. Deterministic (metadata copied; timestamp caller-
    supplied, never generated).
    """

    @abstractmethod
    def record(
        self,
        observation: "ExecutionObservation",
        *,
        conversation_id: str = "",
        metadata: Optional[dict] = None,
        timestamp: Optional[str] = None,
    ) -> "ExecutionRecord":
        """Return an immutable ExecutionRecord for *observation*."""
        raise NotImplementedError


class IExecutionPersistence(ABC):
    """
    Execution persistence prepare step (Phase 8.10) — NOT storage.

    Decides whether an ExecutionRecord is acceptable for persistence and wraps it
    into an immutable PersistenceResult. Never writes files/db/json, serializes,
    or calls any service. Actual storage is a later phase. Depends only on the
    ExecutionRecord. Deterministic (storage_key caller-supplied, never generated).
    """

    @abstractmethod
    def prepare(
        self, record: "ExecutionRecord", *, storage_key: str = ""
    ) -> "PersistenceResult":
        """Return an immutable PersistenceResult for *record*."""
        raise NotImplementedError


class IRuntimePipeline(ABC):
    """
    Runtime Pipeline Orchestrator (Phase 8.11) — the first component that
    understands the whole runtime chain.

    Coordinates the already-existing stages in order (discovery → matching →
    resolution → sandbox → loader → context injection → executor → observer →
    recorder → persistence), stopping on the first failure and returning an
    immutable RuntimePipelineResult. Pure coordination: NO business logic, no
    retries, no branching, no learning, no memory/storage. Depends only on the
    stage interfaces. Nothing calls it automatically (dormant).
    """

    @abstractmethod
    def run(
        self,
        request: "CapabilityRequest",
        *,
        policy: "SandboxPolicy",
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
    ) -> "RuntimePipelineResult":
        """Coordinate the full runtime pipeline; return a RuntimePipelineResult."""
        raise NotImplementedError


class IFailureRecovery(ABC):
    """
    Failure Recovery advisor (Phase 8.12) — descriptive, never acts.

    Consumes an immutable RuntimePipelineResult and returns an immutable
    RecoveryPlan naming WHAT recovery should happen for a failed run. It NEVER
    retries, re-invokes the pipeline, executes, loads, loops, branches into
    orchestration, writes memory, or mutates the result. Like the Evolution
    Engine, it decides WHAT without performing it; a later gated phase may act on
    the plan. Depends only on the RuntimePipelineResult. Pure and deterministic
    (no clocks, ids, entropy, hashing, or I/O). Dormant — nothing calls it.
    """

    @abstractmethod
    def plan(self, result: "RuntimePipelineResult") -> "RecoveryPlan":
        """Return an immutable RecoveryPlan describing recovery for *result*."""
        raise NotImplementedError


class IRuntimeValidator(ABC):
    """
    Runtime Validation checker (Phase 8.13) — read-only integrity assertion.

    Consumes an immutable RuntimePipelineResult and returns an immutable
    ValidationReport asserting the result is internally consistent: the correct
    stage artifacts are present/absent for the outcome, the ``completed`` flag
    agrees with the ``reason``, and the populated stage prefix is contiguous (no
    artifact after a missing earlier stage). It NEVER repairs, re-runs, mutates,
    executes, or recovers — it only checks and reports. Depends only on the
    RuntimePipelineResult. Pure and deterministic (no clocks, ids, entropy,
    hashing, or I/O). Dormant — nothing calls it.
    """

    @abstractmethod
    def validate(self, result: "RuntimePipelineResult") -> "ValidationReport":
        """Return an immutable ValidationReport for *result*."""
        raise NotImplementedError
