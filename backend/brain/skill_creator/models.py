"""
brain/skill_creator/models.py — Phase 7.1: Skill Creator foundation models

Frozen, serializable pydantic value objects. Foundation contracts ONLY —
metadata that describes a skill that MIGHT be created later. These are
architecture drawings, NOT code: no Python, no executable payload, nothing
imported/loaded/installed. Later Phase 7 milestones transform blueprints into
code behind human approval.

Depends only on brain.evolution.models (the Phase 6 output it consumes) +
pydantic/typing. No runtime, BrainCore, Workspace, Planner, or registry imports.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from brain.evolution.models import EvolutionRecommendationSet

# Deterministic lifecycle — the ONLY allowed status values (Phase 7.2.5).
SkillLifecycle = Literal[
    "draft", "validated", "generated", "tested",
    "approved", "installed", "deprecated", "retired",
]

# Canonical permission vocabulary — the ONLY allowed permission strings.
SkillPermission = Literal[
    "filesystem.read", "filesystem.write",
    "workspace.read", "workspace.write",
    "memory.read", "memory.write",
    "network.http", "terminal", "git",
]

# Deterministic engineering-complexity labels.
SkillComplexity = Literal["small", "medium", "large"]

# Frozen future skill-package layout (reserved — nothing generated yet).
_PACKAGE_LAYOUT = {
    "manifest": "manifest.json",
    "implementation": "skill.py",
    "tests": "tests.py",
    "metadata": "metadata.json",
    "readme": "README.md",
    "provenance": "provenance.json",
}


def _default_package_layout() -> Dict[str, str]:
    return dict(_PACKAGE_LAYOUT)


def _default_documentation() -> Dict[str, bool]:
    return {"readme": True, "examples": True, "developer_notes": False}


def _default_risk_profile() -> Dict[str, bool]:
    return {
        "filesystem": False,
        "network": False,
        "shell": False,
        "workspace": False,
        "memory": False,
    }


# Deterministic reservation defaults (declarations only — NOT results, NOT
# behavior). Each describes what a FUTURE pipeline stage will consume/produce.

def _default_expected_quality_dimensions() -> Tuple[str, ...]:
    return (
        "correctness", "maintainability", "security",
        "documentation", "performance", "testability",
    )


class VerificationContract(BaseModel):
    """Reserved declaration of what future verification (Phase 7.3) will check.
    Metadata only — no verification logic, no execution."""

    model_config = ConfigDict(frozen=True)

    expected_checks: Tuple[str, ...] = ("schema", "capabilities", "permissions", "risk")
    required_test_categories: Tuple[str, ...] = ("unit", "determinism", "safety")
    minimum_pass_requirements: Dict[str, int] = Field(
        default_factory=lambda: {"unit": 1, "determinism": 1, "safety": 1}
    )


class GenerationContract(BaseModel):
    """Reserved declaration of what future generation will produce.
    Metadata only — no generator, no filesystem."""

    model_config = ConfigDict(frozen=True)

    expected_output_packages: Tuple[str, ...] = ("skill",)
    expected_module_layout: Dict[str, str] = Field(default_factory=_default_package_layout)
    expected_manifest_version: str = "1.0"
    expected_registry_entries: int = 1


class InstallationContract(BaseModel):
    """Reserved declaration for future installation. Metadata only — no installer."""

    model_config = ConfigDict(frozen=True)

    install_targets: Tuple[str, ...] = ()
    rollback_targets: Tuple[str, ...] = ()
    activation_strategy: str = "manual_approval"
    dependency_strategy: str = "declare_only"


class MarketplaceIdentity(BaseModel):
    """Reserved marketplace/portability identity. Metadata only — no networking."""

    model_config = ConfigDict(frozen=True)

    exportable_identity: str = ""
    marketplace_tags: Tuple[str, ...] = ()
    compatibility_family: str = ""
    semantic_version_strategy: str = "semver"


class SkillBlueprint(BaseModel):
    """
    Immutable metadata describing a skill that COULD be created (Phase 7.1–7.2.5).

    A blueprint is descriptive only — no code, no callables, no executable
    payload. It is an architect's drawing. Later Phase 7 milestones transform
    blueprints into code behind human approval.

    Deterministic: ``id`` and ``canonical_signature`` are derived by the builder
    (no UUID, no timestamp, no hash). Every blueprint carries
    ``recommendation_id`` (mandatory audit trail), schema/compatibility metadata,
    a structured risk profile, a canonical permission vocabulary, Skill DNA, a
    deterministic complexity label, generation-cost estimates, documentation and
    changelog reservations, a frozen ``package_layout``, capability declarations,
    ``approval_required=True``, and a deterministic lifecycle starting at "draft".
    All fields are metadata only — nothing here has behavior.
    """

    model_config = ConfigDict(frozen=True)

    # ---- identity + audit trail ---------------------------------------
    id: str
    recommendation_id: str                        # mandatory — traceability
    blueprint_schema_version: str = "1.0"
    canonical_signature: str = ""                 # deterministic metadata repr (not a hash)

    # ---- descriptive metadata -----------------------------------------
    name: str = ""
    description: str = ""
    purpose: str = ""
    skill_kind: str = ""                          # mapped kind (deterministic)
    skill_family: str = ""                        # sibling grouping (deterministic)
    semantic_fingerprint: str = ""                # semantic identity (NOT a hash)
    human_summary: str = ""                       # deterministic one-sentence why
    source_recommendation_ids: List[str] = Field(default_factory=list)
    skill_dna: Tuple[str, ...] = ()               # lowercase semantic tags, max 8

    # ---- capability declarations (frozen here, never inferred later) --
    provided_capabilities: List[str] = Field(default_factory=list)
    required_capabilities: List[str] = Field(default_factory=list)

    # ---- lifecycle + safety -------------------------------------------
    status: SkillLifecycle = "draft"              # 7.2 always emits "draft"
    approval_required: bool = True                # can never be bypassed

    # ---- runtime compatibility (reserved — no checking yet) -----------
    minimum_runtime_version: str = "2.6.0"
    minimum_api_version: str = "1.0"

    # ---- engineering complexity + generation cost (deterministic) -----
    engineering_complexity: SkillComplexity = "small"
    estimated_complexity: str = "unknown"         # legacy descriptive label
    estimated_tokens: int = 0
    estimated_files: int = 0
    estimated_test_count: int = 0
    estimated_runtime: Optional[float] = None
    estimated_generation_tokens: int = 0
    estimated_generation_steps: int = 0
    confidence: float = 0.0

    # ---- structured risk profile + canonical permissions --------------
    risk_profile: Dict[str, bool] = Field(default_factory=_default_risk_profile)
    risk_level: str = "unknown"                   # legacy descriptive label
    required_permissions: List[SkillPermission] = Field(default_factory=list)

    # ---- documentation + changelog reservations (metadata only) -------
    documentation: Dict[str, bool] = Field(default_factory=_default_documentation)
    include_changelog: bool = True

    # ---- rollback + reserved future package format --------------------
    rollback_strategy: str = "remove_generated_skill"
    package_layout: Dict[str, str] = Field(default_factory=_default_package_layout)

    # ---- reserved extension fields (no behavior) ----------------------
    version: str = "0.0.0"
    dependencies: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    verification_requirements: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # ---- FINAL FREEZE reservations (Phase 7.2.6 — declarations only) --
    # Each declares what a FUTURE pipeline stage will consume/produce. None of
    # these carry behavior; they exist so later phases add NEW immutable stage
    # models without ever modifying this schema (see ADR-0010, ADR-0011).
    expected_quality_dimensions: Tuple[str, ...] = Field(
        default_factory=_default_expected_quality_dimensions
    )
    verification_contract: VerificationContract = Field(default_factory=VerificationContract)
    generation_contract: GenerationContract = Field(default_factory=GenerationContract)
    installation_contract: InstallationContract = Field(default_factory=InstallationContract)
    marketplace_identity: MarketplaceIdentity = Field(default_factory=MarketplaceIdentity)


class SkillBlueprintSet(BaseModel):
    """Immutable collection of SkillBlueprint records (Phase 7.1)."""

    model_config = ConfigDict(frozen=True)

    blueprints: List[SkillBlueprint] = Field(default_factory=list)
    blueprint_count: int = 0


class SkillGenerationRequest(BaseModel):
    """
    Immutable request to derive blueprints from evolution recommendations
    (Phase 7.1).

    Carries the Phase 6 ``EvolutionRecommendationSet`` plus human approval
    metadata (descriptive — no runtime object, no callable). Blueprint
    derivation is NOT execution: nothing here creates or runs code.
    """

    model_config = ConfigDict(frozen=True)

    recommendations: EvolutionRecommendationSet
    approved_by: str = ""
    approval_note: str = ""
    approved: bool = False


class SkillGenerationResult(BaseModel):
    """
    Immutable, descriptive outcome of a blueprint-derivation pass (Phase 7.1).

    Reports which recommendation ids were accepted / rejected as blueprint
    candidates and why. Contains NO code and performs no action.
    """

    model_config = ConfigDict(frozen=True)

    accepted: List[str] = Field(default_factory=list)
    rejected: List[str] = Field(default_factory=list)
    reason: str = ""


class VerificationResult(BaseModel):
    """
    Immutable output of the Verification stage (Phase 7.3, pipeline stage 02).

    Records the outcome of static checks run against ONE SkillBlueprint. Purely
    descriptive: per-check pass/fail, a list of failure reasons, and an overall
    boolean verdict. Contains no code, mutates nothing, and is produced
    deterministically from the blueprint alone.
    """

    model_config = ConfigDict(frozen=True)

    blueprint_id: str
    recommendation_id: str = ""
    passed: bool = False
    checks: Dict[str, bool] = Field(default_factory=dict)
    failures: List[str] = Field(default_factory=list)


class GenerationResult(BaseModel):
    """
    Immutable output of the Generation stage (Phase 7.4, pipeline stage 03).

    Describes the skill package that WOULD be produced for a verified blueprint:
    package name, manifest version, and a deterministic map of relative file
    path -> file content (as strings). Generation records WHAT was produced;
    writing to disk is an installation concern (stage 06). Nothing is executed.

    ``generated`` is False when the input verification did not pass (gated); in
    that case ``files`` is empty. Produced deterministically from the blueprint
    + verification result alone.
    """

    model_config = ConfigDict(frozen=True)

    blueprint_id: str
    recommendation_id: str = ""
    generated: bool = False
    package_name: str = ""
    manifest_version: str = "1.0"
    files: Dict[str, str] = Field(default_factory=dict)
    skipped_reason: str = ""


class TestResult(BaseModel):
    """
    Immutable output of the Testing stage (Phase 7.5, pipeline stage 04).

    Records the outcome of statically evaluating a generated package against the
    test categories the blueprint declared. Descriptive: per-category pass/fail,
    total categories, and an overall verdict. ``tested`` is False when the input
    generation did not produce a package (gated). Produced deterministically from
    the generation result + blueprint alone; no code is executed.
    """

    model_config = ConfigDict(frozen=True)

    blueprint_id: str
    recommendation_id: str = ""
    tested: bool = False
    passed: bool = False
    categories: Dict[str, bool] = Field(default_factory=dict)
    failures: List[str] = Field(default_factory=list)
    skipped_reason: str = ""


class ApprovalRecord(BaseModel):
    """
    Immutable output of the Approval stage (Phase 7.6, pipeline stage 05).

    The mandatory human gate. Records an explicit human decision about a tested
    skill package. The approval decision is EXTERNAL input (never generated); a
    passing TestResult is a precondition. ``approved`` is never True unless the
    caller explicitly supplied approval AND the TestResult passed.

    ``approval_timestamp`` is caller-supplied (Optional); this stage never
    generates a timestamp. Produced deterministically from (TestResult + supplied
    approval metadata).
    """

    model_config = ConfigDict(frozen=True)

    blueprint_id: str
    recommendation_id: str = ""
    approved: bool = False
    approver: str = ""
    decision_reason: str = ""
    approval_timestamp: Optional[str] = None
    skipped_reason: str = ""


class InstallationRecord(BaseModel):
    """
    Immutable output of the Installation stage (Phase 7.7, pipeline stage 06).

    Records the facts of materializing an approved generated package to disk.
    The first pipeline stage allowed filesystem writes — but it only copies the
    files already described in GenerationResult.files (never regenerates,
    executes, activates, or registers). ``installed`` is False when the input
    approval was not granted (gated).

    Deterministic: installing the same GenerationResult to the same location
    yields the same filesystem state (idempotent) and a byte-identical
    InstallationRecord. No generated timestamps/uuids.
    """

    model_config = ConfigDict(frozen=True)

    blueprint_id: str
    recommendation_id: str = ""
    installed: bool = False
    installed_location: str = ""
    installed_files: List[str] = Field(default_factory=list)
    installation_mode: str = ""
    skipped_reason: str = ""


class RegistryEntry(BaseModel):
    """
    Immutable output of the Registry stage (Phase 7.8, pipeline stage 07).

    Records the catalog fact of an installed skill: its deterministic identity
    (semantic_fingerprint, skill_family), package name, a derived registry_key,
    and installed location. Append-only — supersession is a NEW entry, never an
    edit. ``registration_status`` is "registered" on success, or "skipped" when
    the input was not installed.

    Deterministic: derived purely from (InstallationRecord + SkillBlueprint). No
    timestamps, uuids, or hashing.
    """

    model_config = ConfigDict(frozen=True)

    blueprint_id: str
    recommendation_id: str = ""
    semantic_fingerprint: str = ""
    skill_family: str = ""
    package_name: str = ""
    registry_key: str = ""
    installed_location: str = ""
    registration_status: str = "skipped"


class LifecycleEvent(BaseModel):
    """
    Immutable output of the Lifecycle stage (Phase 7.9, pipeline stage 08).

    One append-only event recording a state transition of a registered skill.
    The lifecycle history is an append-only log — events are never edited or
    deleted; supersession is another event. ``status`` is "transitioned" on a
    legal transition, or "skipped" (with skipped_reason) when the registry entry
    is not registered or the transition is illegal.

    Deterministic: derived purely from (RegistryEntry + supplied transition). No
    timestamps, uuids, or generated ids.
    """

    model_config = ConfigDict(frozen=True)

    blueprint_id: str
    recommendation_id: str = ""
    registry_key: str = ""
    previous_state: str = ""
    new_state: str = ""
    transition: str = ""
    transition_reason: str = ""
    actor: str = ""
    status: str = "skipped"
    skipped_reason: str = ""


class MarketplaceManifest(BaseModel):
    """
    Immutable output of the Marketplace stage (Phase 7.10, pipeline stage 09).

    A purely descriptive, portable marketplace descriptor for a registered skill.
    Every value is copied from the RegistryEntry or the blueprint's frozen
    ``marketplace_identity`` — nothing is invented, hashed, timestamped, or
    fetched. ``manifest_status`` is "published" for a registered entry (manifest
    constructed — NO networking), or "skipped" otherwise.

    Deterministic: a pure function of (RegistryEntry + SkillBlueprint).
    """

    model_config = ConfigDict(frozen=True)

    blueprint_id: str
    recommendation_id: str = ""
    registry_key: str = ""
    package_name: str = ""
    semantic_fingerprint: str = ""
    skill_family: str = ""
    title: str = ""
    description: str = ""
    version: str = ""
    author: str = ""
    license: str = ""
    tags: Tuple[str, ...] = ()
    categories: Tuple[str, ...] = ()
    homepage: str = ""
    repository: str = ""
    documentation: str = ""
    manifest_status: str = "skipped"


class RollbackRecord(BaseModel):
    """
    Immutable output of the Rollback stage (Phase 7.11, pipeline stage 10).

    Records reversing the filesystem materialization done by BlueprintInstaller.
    Deletes ONLY the files the installer created (InstallationRecord.installed_
    files), scoped under installed_location, then prunes directories it empties.
    Append-only artifact — never edits any prior record. ``rollback_performed``
    is False when the input was not installed (gated).

    Deterministic + idempotent: rolling back the same InstallationRecord twice
    yields the same filesystem state and a byte-identical RollbackRecord. No
    timestamps, uuids, or hashing.
    """

    model_config = ConfigDict(frozen=True)

    blueprint_id: str
    recommendation_id: str = ""
    rollback_performed: bool = False
    rollback_location: str = ""
    removed_files: List[str] = Field(default_factory=list)
    rollback_strategy: str = ""
    rollback_status: str = "skipped"
    skipped_reason: str = ""
