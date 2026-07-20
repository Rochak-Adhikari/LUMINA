"""
brain/skill_creator — LUMINA Skill Creator (Phase 7.0)

Phase 7 performs the evolution that Phase 6 only recommends. It consumes the
frozen EvolutionRecommendationSet and, behind human approval, will eventually
generate, validate, install, and register skills.

Phase 7.1 — Foundation (contracts only)
---------------------------------------
  models.py      SkillBlueprint, SkillBlueprintSet, SkillGenerationRequest,
                 SkillGenerationResult — frozen, descriptive metadata only
  interfaces.py  ISkillCreator — blueprint-creation contract

Phase 7.2 — Blueprint Builder
-----------------------------
  blueprint_builder.py  BlueprintBuilder — deterministic
                        EvolutionRecommendationSet → SkillBlueprintSet
                        (metadata only; no code, no files, no install)

Blueprints are architecture drawings, NOT code: nothing here is Python,
executable, imported, loaded, or installed. No generator, validator, or
installer exists yet. BlueprintBuilder is registered DORMANT (no runtime path
consumes it); runtime is byte-identical.
"""

from brain.skill_creator.models import (
    SkillBlueprint,
    SkillBlueprintSet,
    SkillGenerationRequest,
    SkillGenerationResult,
    VerificationContract,
    GenerationContract,
    InstallationContract,
    MarketplaceIdentity,
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
from brain.skill_creator.interfaces import (
    ISkillCreator,
    IBlueprintVerifier,
    IBlueprintGenerator,
    IBlueprintTester,
    IBlueprintApprover,
    IBlueprintInstaller,
    IBlueprintRegistry,
    ILifecycleManager,
    IMarketplacePublisher,
    IRollbackManager,
)
from brain.skill_creator.blueprint_builder import BlueprintBuilder
from brain.skill_creator.blueprint_verifier import BlueprintVerifier
from brain.skill_creator.blueprint_generator import BlueprintGenerator
from brain.skill_creator.blueprint_tester import BlueprintTester
from brain.skill_creator.blueprint_approver import BlueprintApprover
from brain.skill_creator.blueprint_installer import BlueprintInstaller
from brain.skill_creator.blueprint_registry import BlueprintRegistry
from brain.skill_creator.lifecycle_manager import LifecycleManager
from brain.skill_creator.marketplace_publisher import MarketplacePublisher
from brain.skill_creator.rollback_manager import RollbackManager

__all__ = [
    "SkillBlueprint",
    "SkillBlueprintSet",
    "SkillGenerationRequest",
    "SkillGenerationResult",
    "VerificationContract",
    "GenerationContract",
    "InstallationContract",
    "MarketplaceIdentity",
    "VerificationResult",
    "GenerationResult",
    "TestResult",
    "ApprovalRecord",
    "InstallationRecord",
    "RegistryEntry",
    "LifecycleEvent",
    "MarketplaceManifest",
    "RollbackRecord",
    "ISkillCreator",
    "IBlueprintVerifier",
    "IBlueprintGenerator",
    "IBlueprintTester",
    "IBlueprintApprover",
    "IBlueprintInstaller",
    "IBlueprintRegistry",
    "ILifecycleManager",
    "IMarketplacePublisher",
    "IRollbackManager",
    "BlueprintBuilder",
    "BlueprintVerifier",
    "BlueprintGenerator",
    "BlueprintTester",
    "BlueprintApprover",
    "BlueprintInstaller",
    "BlueprintRegistry",
    "LifecycleManager",
    "MarketplacePublisher",
    "RollbackManager",
]
