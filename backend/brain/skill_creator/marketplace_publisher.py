"""
brain/skill_creator/marketplace_publisher.py — Phase 7.10: MarketplacePublisher

Pipeline stage 09 (Marketplace) — an OPTIONAL side branch off the registry.
Consumes ONE RegistryEntry plus its SkillBlueprint and produces ONE immutable
MarketplaceManifest: a purely descriptive, portable marketplace descriptor.

"Publisher" refers ONLY to manifest construction. This performs NO networking,
uploads, downloads, HTTP, sockets, filesystem, subprocess, or execution, and
mutates no prior artifact. Every manifest value is copied from the RegistryEntry
or the blueprint's frozen ``marketplace_identity`` — nothing is invented,
hashed, timestamped, or generated.

Gated: only a registered RegistryEntry yields manifest_status="published";
otherwise "skipped". Deterministic — a pure function of (RegistryEntry +
SkillBlueprint), no internal state.

Depends only on brain.skill_creator.models, brain.skill_creator.interfaces.
"""

from __future__ import annotations

from brain.skill_creator.interfaces import IMarketplacePublisher
from brain.skill_creator.models import (
    RegistryEntry,
    SkillBlueprint,
    MarketplaceManifest,
)


class MarketplacePublisher(IMarketplacePublisher):
    """Deterministic marketplace-manifest constructor. Owns no state."""

    def publish(
        self, registry_entry: RegistryEntry, blueprint: SkillBlueprint
    ) -> MarketplaceManifest:
        identity = blueprint.marketplace_identity
        registered = registry_entry.registration_status == "registered"

        return MarketplaceManifest(
            blueprint_id=registry_entry.blueprint_id,
            recommendation_id=registry_entry.recommendation_id,
            registry_key=registry_entry.registry_key,
            package_name=registry_entry.package_name,
            semantic_fingerprint=registry_entry.semantic_fingerprint,
            skill_family=registry_entry.skill_family,
            title=blueprint.name,
            description=blueprint.description,
            version=blueprint.version,
            author=blueprint.provenance.get("generated_by", ""),
            license=str(blueprint.metadata.get("license", "")),
            tags=identity.marketplace_tags,
            categories=(identity.compatibility_family,) if identity.compatibility_family else (),
            homepage=str(blueprint.metadata.get("homepage", "")),
            repository=str(blueprint.metadata.get("repository", "")),
            documentation=str(blueprint.metadata.get("documentation", "")),
            manifest_status="published" if registered else "skipped",
        )
