"""
brain/skill_runtime/models.py — Phase 8.1: Skill Runtime discovery models

Frozen, serializable pydantic value objects — the immutable outputs of the
Registry Discovery stage. Descriptive only: a DiscoveredSkill is a read-only
projection of a RegistryEntry (never the RegistryEntry itself, never an
executable payload). A RegistrySearchResult is the deterministic result set of a
discovery query.

Deterministic: derived purely from the queried RegistryEntry list + query
inputs. No clocks, identifiers, entropy, hashing, environment, or I/O.

Depends only on pydantic/typing. No runtime, BrainCore, Planner, Registry, or
skill_creator imports (a DiscoveredSkill carries primitive fields copied from a
RegistryEntry, so this module needs no upward dependency).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


class DiscoveredSkill(BaseModel):
    """
    Immutable, read-only projection of a single registered skill.

    A descriptive catalog record for runtime discovery — the identity and
    location of an installed skill, copied out of a RegistryEntry. Carries NO
    executable code and NO reference to the RegistryEntry object, so consumers
    cannot mutate the frozen Phase 7 catalog through it.
    """

    model_config = ConfigDict(frozen=True)

    blueprint_id: str
    recommendation_id: str = ""
    semantic_fingerprint: str = ""
    skill_family: str = ""
    package_name: str = ""
    registry_key: str = ""
    installed_location: str = ""
    registration_status: str = ""


class RegistrySearchResult(BaseModel):
    """
    Immutable output of Registry Discovery (Phase 8.1).

    The deterministic result set of a discovery query over the registry:
    the matched skills (ordered deterministically), the total count, and the
    query string that produced them (empty string = "list everything").
    """

    model_config = ConfigDict(frozen=True)

    skills: List[DiscoveredSkill] = Field(default_factory=list)
    total_count: int = 0
    query: str = ""


# ---- Phase 8.2: Capability Matching ------------------------------------


class CapabilityRequest(BaseModel):
    """
    Immutable input to Capability Matching (Phase 8.2).

    A semantic ask — "which installed skills satisfy this capability?" — carrying
    only the requested capability plus optional deterministic restrictions. No
    runtime objects, no executable payload, no RegistryEntry.

    version_preference is accepted for forward-compatibility but is currently
    inert: the frozen Phase 7 RegistryEntry (and thus the 8.1 DiscoveredSkill
    projection) carries no version, so version ranking is deferred to Phase 8.9.
    """

    model_config = ConfigDict(frozen=True)

    capability: str = ""
    family: Optional[str] = None
    package: Optional[str] = None
    tags: Tuple[str, ...] = ()
    version_preference: str = ""


class CapabilityMatch(BaseModel):
    """
    Immutable pairing of a discovered skill with its deterministic match signal.

    Wraps the read-only DiscoveredSkill (never a RegistryEntry) plus an integer
    score and a human-readable reason describing which rule fired. Carries no
    executable payload.
    """

    model_config = ConfigDict(frozen=True)

    skill: DiscoveredSkill
    score: int = 0
    reason: str = ""


class CapabilityMatchResult(BaseModel):
    """
    Immutable output of Capability Matching (Phase 8.2).

    The deterministically ordered candidate skills that satisfy a
    CapabilityRequest (score descending, then skill_family / package_name /
    registry_key), the match count, and the requested capability echoed back.
    """

    model_config = ConfigDict(frozen=True)

    matches: List[CapabilityMatch] = Field(default_factory=list)
    match_count: int = 0
    capability: str = ""


# ---- Phase 8.3: Dependency Resolution ----------------------------------


class DependencyRequirement(BaseModel):
    """
    Immutable declaration of one thing a skill needs before it may run.

    ``kind`` is a free-form category ("permission", "runtime", "capability",
    "version") and ``value`` its target. ``satisfied`` records whether resolution
    confirmed it; ``detail`` explains why not when unsatisfied. Descriptive only —
    no runtime objects, no execution.
    """

    model_config = ConfigDict(frozen=True)

    kind: str
    value: str = ""
    satisfied: bool = False
    detail: str = ""


class DependencyResolution(BaseModel):
    """
    Immutable output of Dependency Resolution (Phase 8.3).

    Records whether the selected skill is ready to proceed to loading/execution.
    ``resolved`` is True only when every requirement is satisfied. ``skill`` is
    the chosen DiscoveredSkill (top-ranked satisfiable match), or None when no
    candidate qualifies. ``requirements`` is the deterministic checklist;
    ``unsatisfied`` echoes the failing requirement values for quick inspection.

    Deterministic: a pure function of the CapabilityMatchResult + supplied
    grants. No clocks, identifiers, entropy, hashing, or I/O.
    """

    model_config = ConfigDict(frozen=True)

    resolved: bool = False
    skill: Optional[DiscoveredSkill] = None
    requirements: List[DependencyRequirement] = Field(default_factory=list)
    unsatisfied: Tuple[str, ...] = ()
    reason: str = ""


# ---- Phase 8.4: Skill Sandbox ------------------------------------------


class SandboxPolicy(BaseModel):
    """
    Immutable runtime safety policy supplied to the Sandbox (Phase 8.4).

    Descriptive constraints only — the sandbox is a gatekeeper, not an executor.
    ``allowed_permissions`` is the set of permission grants the runtime will
    tolerate; a resolved skill carrying a permission outside this set is denied.
    ``require_resolved`` (default True) demands a successful DependencyResolution.
    ``max_risk`` names the highest risk tier allowed (informational; risk data is
    not in the frozen projection — see ADR).
    """

    model_config = ConfigDict(frozen=True)

    allowed_permissions: Tuple[str, ...] = ()
    require_resolved: bool = True
    max_risk: str = "unknown"


class SandboxDecision(BaseModel):
    """
    Immutable output of the Skill Sandbox (Phase 8.4).

    A pure allow/deny verdict on whether a resolved skill MAY execute — no
    loading, no execution. ``approved`` is True only when every policy check
    passes. ``skill`` echoes the candidate (None when denied before a skill is
    available). ``violations`` lists the failing checks; ``reason`` summarizes.

    Deterministic: a pure function of (DependencyResolution + SandboxPolicy).
    """

    model_config = ConfigDict(frozen=True)

    approved: bool = False
    skill: Optional[DiscoveredSkill] = None
    violations: Tuple[str, ...] = ()
    reason: str = ""


# ---- Phase 8.5: Skill Loader -------------------------------------------


class LoadedSkill(BaseModel):
    """
    Immutable result of the Skill Loader (Phase 8.5).

    Turns an approved skill description into a loaded, ready-to-execute instance.
    ``loaded`` is True only when the module imported, the ``Skill`` class
    instantiated, and the required ``execute``/``run`` interface validated.
    ``instance`` holds the live skill object (kept read-only via a frozen model;
    the loader does NOT call it — execution is Phase 8.6). ``skill`` echoes the
    approved DiscoveredSkill; ``error`` explains a load failure.

    Not serialized to disk — the model is frozen but permits an arbitrary
    ``instance`` type. Loading is the ONLY side-effecting step here (a module
    import); no execution.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    loaded: bool = False
    skill: Optional[DiscoveredSkill] = None
    instance: Optional[object] = None
    entrypoint: str = ""
    module_path: str = ""
    error: str = ""


# ---- Phase 8.6: Skill Executor -----------------------------------------


class ExecutionResult(BaseModel):
    """
    Immutable result of the Skill Executor (Phase 8.6).

    Records the outcome of calling a loaded skill's canonical ``run(context)``
    exactly once. ``succeeded`` is True only when the call returned without
    raising. ``output`` holds the skill's return value (arbitrary type, kept
    read-only via a frozen model — no execution occurs by reading it).
    ``error`` carries a structured failure summary; the executor NEVER lets an
    exception propagate. ``registry_key`` echoes the executed skill for audit.

    Not serialized to disk — frozen but permits an arbitrary ``output`` type.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    succeeded: bool = False
    output: Optional[object] = None
    registry_key: str = ""
    error: str = ""


# ---- Phase 8.7: Context Injection --------------------------------------


class ExecutionContext(BaseModel):
    """
    Immutable execution context prepared for a skill (Phase 8.7).

    Everything a skill needs to run, packaged as frozen primitive data — no live
    services, no runtime objects, no raw skill instance. Snapshots are plain
    read-only dicts (copied, never live handles). This is what the executor's
    ``run(context)`` receives once wiring is enabled.
    """

    model_config = ConfigDict(frozen=True)

    registry_key: str = ""
    conversation_id: str = ""
    user_input: str = ""
    memory_snapshot: Dict[str, Any] = Field(default_factory=dict)
    workspace_snapshot: Dict[str, Any] = Field(default_factory=dict)
    environment_snapshot: Dict[str, Any] = Field(default_factory=dict)
    available_tools: Tuple[str, ...] = ()
    variables: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextInjectionResult(BaseModel):
    """
    Immutable output of Context Injection (Phase 8.7).

    ``prepared`` is True only when a valid ExecutionContext was built from a
    loaded skill. ``context`` is that frozen ExecutionContext (None when not
    prepared). ``reason`` explains a failure. Pure transformation — no execution,
    no loading, no service access.
    """

    model_config = ConfigDict(frozen=True)

    prepared: bool = False
    context: Optional[ExecutionContext] = None
    reason: str = ""


# ---- Phase 8.8: Execution Observation ----------------------------------


class ExecutionObservation(BaseModel):
    """
    Immutable observational record of one execution outcome (Phase 8.8).

    Descriptive metadata derived purely from an ExecutionResult — no live
    objects, no service references, no mutable state. Purely observational: it
    records what happened, changing nothing.

    ``timestamp`` is caller-supplied (Optional) and NEVER generated inline, so the
    observation stays deterministic (a generated clock value would break
    reproducibility — consistent with the runtime's determinism rule). ``summary``
    is a short deterministic sentence; ``output_type`` is the result output's
    type name ("NoneType" when absent).
    """

    model_config = ConfigDict(frozen=True)

    observed: bool = False
    registry_key: str = ""
    succeeded: bool = False
    error: str = ""
    output_type: str = ""
    timestamp: Optional[str] = None
    summary: str = ""


# ---- Phase 8.9: Execution Recording ------------------------------------


class ExecutionRecord(BaseModel):
    """
    Immutable record prepared from an ExecutionObservation (Phase 8.9).

    A pure transformation of one observation into a persistence-ready record —
    the recorder does NOT persist, log, or save; persistence is a future phase.
    ``metadata`` is copied (never aliased); ``timestamp`` is caller-supplied and
    never generated. No live references, no services. Deterministic.
    """

    model_config = ConfigDict(frozen=True)

    recorded: bool = False
    registry_key: str = ""
    conversation_id: str = ""
    summary: str = ""
    succeeded: bool = False
    output_type: str = ""
    error: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None
    reason: str = ""


# ---- Phase 8.10: Execution Persistence ---------------------------------


class PersistenceResult(BaseModel):
    """
    Immutable result of the Execution Persistence prepare step (Phase 8.10).

    Decides whether an ExecutionRecord is acceptable for persistence and wraps
    it — it does NOT store anything. Actual storage is a later phase.
    ``storage_key`` is caller-supplied and never generated (no hashes, UUIDs, or
    timestamps). ``record`` is the accepted ExecutionRecord (None when not
    persistable). Deterministic; no IO.
    """

    model_config = ConfigDict(frozen=True)

    persistable: bool = False
    record: Optional[ExecutionRecord] = None
    storage_key: str = ""
    reason: str = ""


# ---- Phase 8.11: Runtime Pipeline Orchestrator -------------------------


class RuntimePipelineResult(BaseModel):
    """
    Immutable end-to-end result of the Runtime Pipeline Orchestrator (Phase 8.11).

    Records the output of every completed stage in pipeline order. On the first
    stage failure the orchestrator stops; the remaining fields stay None and
    ``reason`` names the stopping stage. ``completed`` is True only when the whole
    chain (discovery → persistence) finished. Pure coordination — the orchestrator
    holds no business logic; each field is a prior stage's own immutable output.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    completed: bool = False
    registry_key: str = ""
    discovery: Optional[RegistrySearchResult] = None
    match: Optional[CapabilityMatchResult] = None
    resolution: Optional[DependencyResolution] = None
    sandbox: Optional[SandboxDecision] = None
    loaded: Optional[LoadedSkill] = None
    context: Optional[ContextInjectionResult] = None
    execution: Optional[ExecutionResult] = None
    observation: Optional[ExecutionObservation] = None
    record: Optional[ExecutionRecord] = None
    persistence: Optional[PersistenceResult] = None
    reason: str = ""


# ---- Phase 8.12: Failure Recovery --------------------------------------


class RecoveryPlan(BaseModel):
    """
    Immutable, descriptive recovery plan for one pipeline outcome (Phase 8.12).

    Derived purely from a RuntimePipelineResult, it names WHAT recovery *should*
    happen when a run failed — it NEVER retries, re-invokes, executes, loops, or
    mutates anything. Purely descriptive, exactly like the Evolution Engine
    decides WHAT should evolve without performing it. A future phase may act on a
    plan behind an explicit gate; this stage only produces the advice.

    ``needed`` is True only for a failed run (a completed run needs no recovery).
    ``failed_stage`` echoes the stopping stage (the pipeline ``reason``).
    ``strategy`` is a deterministic advisory action from a fixed vocabulary
    (e.g. "none", "retry_transient", "rematch_capability", "review_required",
    "abort"); ``retryable`` flags whether the failure class is transient in
    principle; ``rationale`` is a short deterministic explanation.

    Deterministic: a pure function of the input result — no clocks, ids, entropy,
    hashing, or I/O.
    """

    model_config = ConfigDict(frozen=True)

    needed: bool = False
    completed: bool = False
    failed_stage: str = ""
    registry_key: str = ""
    strategy: str = "none"
    retryable: bool = False
    rationale: str = ""


# ---- Phase 8.13: Runtime Validation ------------------------------------


class ValidationReport(BaseModel):
    """
    Immutable structural-integrity report for one pipeline outcome (Phase 8.13).

    Derived purely from a RuntimePipelineResult, it asserts that the result is
    internally consistent — the correct stage artifacts are present/absent for
    the outcome, the completion flag agrees with the reason, and the populated
    prefix is contiguous (no gaps: a stage artifact never appears after a missing
    earlier stage). It is a READ-ONLY checker: it NEVER repairs, re-runs, mutates,
    executes, or recovers. Like the Evolution Engine, it reports; it performs
    nothing.

    ``valid`` is True only when every invariant holds. ``checked`` counts the
    invariants evaluated. ``violations`` is a deterministic, ordered tuple of
    short violation codes (empty when valid). ``last_stage`` names the last
    populated stage in pipeline order ("" when none). ``completed`` echoes the
    result's completion flag for convenience.

    Deterministic: a pure function of the input result — no clocks, ids, entropy,
    hashing, or I/O.
    """

    model_config = ConfigDict(frozen=True)

    valid: bool = False
    completed: bool = False
    checked: int = 0
    last_stage: str = ""
    violations: Tuple[str, ...] = ()
