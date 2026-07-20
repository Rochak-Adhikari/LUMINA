"""
brain/skill_creator/interfaces.py — Phase 7.1: Skill Creator foundation contract

Behaviour-only contract for blueprint creation. No installer, no generator, no
validator — those are later Phase 7 milestones. Imports only stdlib/abc +
skill_creator/evolution models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from brain.evolution.models import EvolutionRecommendationSet
from brain.skill_creator.models import (
    SkillBlueprint,
    SkillBlueprintSet,
    VerificationResult,
    GenerationResult,
    TestResult,
    ApprovalRecord,
    InstallationRecord,
    RegistryEntry,
    LifecycleEvent,
    MarketplaceManifest,
    RollbackRecord,
)


class ISkillCreator(ABC):
    """
    Blueprint-creation contract (Phase 7.1).

    Consumes an EvolutionRecommendationSet (Phase 6 output) and produces a
    SkillBlueprintSet — descriptive metadata only. It creates NO code, installs
    nothing, executes nothing. Deterministic and read-only over its input.
    """

    @abstractmethod
    def create_blueprint(
        self, recommendations: EvolutionRecommendationSet
    ) -> SkillBlueprintSet:
        """Derive descriptive skill blueprints from *recommendations*."""


class IBlueprintVerifier(ABC):
    """
    Blueprint verification contract (Phase 7.3, pipeline stage 02).

    Consumes ONE immutable SkillBlueprint and produces ONE immutable
    VerificationResult. Static checks only — reads the blueprint's declared
    metadata against its own verification_contract. Never mutates the blueprint,
    generates code, touches the filesystem, or executes anything. Deterministic.
    """

    @abstractmethod
    def verify(self, blueprint: SkillBlueprint) -> VerificationResult:
        """Statically verify *blueprint*; return an immutable VerificationResult."""


class IBlueprintGenerator(ABC):
    """
    Blueprint generation contract (Phase 7.4, pipeline stage 03).

    Consumes ONE immutable SkillBlueprint plus its VerificationResult and
    produces ONE immutable GenerationResult describing the skill package's files.
    Gated: generation only proceeds when verification passed. Never writes to the
    filesystem, installs, or executes anything. Deterministic — same inputs yield
    a byte-identical GenerationResult.
    """

    @abstractmethod
    def generate(
        self, blueprint: SkillBlueprint, verification: VerificationResult
    ) -> GenerationResult:
        """Produce a GenerationResult from a verified *blueprint*."""


class IBlueprintTester(ABC):
    """
    Blueprint testing contract (Phase 7.5, pipeline stage 04).

    Consumes ONE immutable GenerationResult plus its SkillBlueprint and produces
    ONE immutable TestResult. Statically evaluates the generated package against
    the blueprint's declared required_test_categories / minimum_pass_requirements.
    Gated: testing only proceeds when generation produced a package. Never
    executes code, writes files, or installs anything. Deterministic.
    """

    @abstractmethod
    def test(
        self, blueprint: SkillBlueprint, generation: GenerationResult
    ) -> TestResult:
        """Statically test a generated package; return an immutable TestResult."""


class IBlueprintApprover(ABC):
    """
    Blueprint approval contract (Phase 7.6, pipeline stage 05).

    The mandatory human gate. Consumes ONE immutable TestResult plus an EXPLICIT
    human decision (supplied by the caller) and produces ONE immutable
    ApprovalRecord. Never auto-approves, never fabricates a decision. Approval
    requires both a passing TestResult and an explicit ``approve=True`` from the
    caller. Deterministic — the record is a pure function of its inputs; no
    timestamp is generated (caller supplies one if desired).
    """

    @abstractmethod
    def review(
        self,
        test_result: TestResult,
        *,
        approver: str,
        approve: bool,
        decision_reason: str = "",
        approval_timestamp: Optional[str] = None,
    ) -> ApprovalRecord:
        """Record an explicit human approval decision over *test_result*."""


class IBlueprintInstaller(ABC):
    """
    Blueprint installation contract (Phase 7.7, pipeline stage 06).

    Consumes an approved ApprovalRecord plus its GenerationResult and materializes
    the generated package's files under a caller-supplied target root. The first
    pipeline stage permitted filesystem writes. Gated: installs only when
    ApprovalRecord.approved is True. Never regenerates, executes, imports,
    activates, or registers. Idempotent and deterministic — reinstalling the same
    GenerationResult yields the same filesystem state and InstallationRecord.
    """

    @abstractmethod
    def install(
        self,
        approval: ApprovalRecord,
        generation: GenerationResult,
        target_root: str,
    ) -> InstallationRecord:
        """Materialize the approved generated package under *target_root*."""


class IBlueprintRegistry(ABC):
    """
    Blueprint registry contract (Phase 7.8, pipeline stage 07).

    Consumes an installed InstallationRecord plus its SkillBlueprint and appends
    one immutable RegistryEntry to an append-only catalog. Gated: registers only
    when InstallationRecord.installed is True. Never installs, regenerates,
    overwrites, or mutates existing entries — supersession is a NEW entry.
    Deterministic: the entry (and its registry_key) is a pure function of the
    inputs.
    """

    @abstractmethod
    def register(
        self, installation: InstallationRecord, blueprint: SkillBlueprint
    ) -> RegistryEntry:
        """Append a RegistryEntry for an installed skill; return that entry."""

    @abstractmethod
    def entries(self) -> List[RegistryEntry]:
        """Return all registered entries in append order (copy)."""

    @abstractmethod
    def get(self, registry_key: str) -> Optional[RegistryEntry]:
        """Return the most-recently appended entry for *registry_key*, or None."""


class ILifecycleManager(ABC):
    """
    Skill lifecycle contract (Phase 7.9, pipeline stage 08).

    Consumes a RegistryEntry plus an EXPLICIT transition intent supplied by the
    caller and appends one immutable LifecycleEvent to an append-only log. Never
    edits or replaces RegistryEntry or prior events. Gated: transitions only a
    registered entry; rejects illegal transitions with status="skipped".
    Deterministic — the event is a pure function of (entry, current state,
    transition).
    """

    @abstractmethod
    def transition(
        self,
        registry_entry: RegistryEntry,
        transition: str,
        *,
        actor: str = "",
        transition_reason: str = "",
    ) -> LifecycleEvent:
        """Apply an explicit *transition* to a registered skill; append an event."""

    @abstractmethod
    def events(self) -> List[LifecycleEvent]:
        """Return the append-only lifecycle log (copy)."""

    @abstractmethod
    def current_state(self, registry_key: str) -> str:
        """Return the latest lifecycle state for *registry_key* ("registered" default)."""


class IMarketplacePublisher(ABC):
    """
    Marketplace manifest contract (Phase 7.10, pipeline stage 09).

    Consumes ONE RegistryEntry plus its SkillBlueprint and produces ONE immutable
    MarketplaceManifest — a purely descriptive, portable marketplace descriptor.
    "Publisher" refers ONLY to manifest construction: this NEVER performs
    networking, uploads, downloads, HTTP, sockets, or any I/O, and never mutates
    any prior artifact. Gated: only a registered entry yields
    manifest_status="published". Deterministic.
    """

    @abstractmethod
    def publish(
        self, registry_entry: RegistryEntry, blueprint: SkillBlueprint
    ) -> MarketplaceManifest:
        """Construct a MarketplaceManifest for a registered skill (no networking)."""


class IRollbackManager(ABC):
    """
    Rollback contract (Phase 7.11, pipeline stage 10) — the final stage.

    Consumes an InstallationRecord plus its SkillBlueprint and produces ONE
    immutable RollbackRecord, reversing ONLY the filesystem materialization done
    by BlueprintInstaller. Gated: rolls back only when installed. Deletes only
    installer-created files scoped under installed_location, then prunes emptied
    directories. Never edits any prior artifact, executes, or imports generated
    code. Deterministic + idempotent.
    """

    @abstractmethod
    def rollback(
        self, installation: InstallationRecord, blueprint: SkillBlueprint
    ) -> RollbackRecord:
        """Reverse an installation; return an immutable RollbackRecord."""
