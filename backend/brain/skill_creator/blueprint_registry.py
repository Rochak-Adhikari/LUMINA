"""
brain/skill_creator/blueprint_registry.py — Phase 7.8: BlueprintRegistry

Pipeline stage 07 (Registry). Consumes an installed InstallationRecord plus its
SkillBlueprint and appends ONE immutable RegistryEntry to an append-only catalog.

Rules:
  - Gated: registers only when InstallationRecord.installed is True; otherwise
    returns a "skipped" entry and appends nothing.
  - Append-only: never overwrites, mutates, or replaces an existing entry.
    Re-registering the same skill appends ANOTHER immutable entry (supersession);
    get() returns the most-recently appended entry for a key.
  - Never installs, regenerates, or touches previous pipeline artifacts.

Deterministic: the RegistryEntry (and its registry_key = semantic_fingerprint)
is a pure function of the inputs. No uuid, datetime, random, hashing,
environment, subprocess, network, filesystem, or execution.

Depends only on brain.skill_creator.models, brain.skill_creator.interfaces,
typing.
"""

from __future__ import annotations

from typing import List, Optional

from brain.skill_creator.interfaces import IBlueprintRegistry
from brain.skill_creator.models import (
    InstallationRecord,
    SkillBlueprint,
    RegistryEntry,
)


class BlueprintRegistry(IBlueprintRegistry):
    """Append-only, deterministic catalog of installed skills."""

    def __init__(self) -> None:
        self._entries: List[RegistryEntry] = []

    def register(
        self, installation: InstallationRecord, blueprint: SkillBlueprint
    ) -> RegistryEntry:
        # Gate: only installed skills may be registered.
        if not installation.installed:
            return RegistryEntry(
                blueprint_id=blueprint.id,
                recommendation_id=blueprint.recommendation_id,
                semantic_fingerprint=blueprint.semantic_fingerprint,
                skill_family=blueprint.skill_family,
                package_name=blueprint.name,
                registry_key=blueprint.semantic_fingerprint,
                installed_location=installation.installed_location,
                registration_status="skipped",
            )

        entry = RegistryEntry(
            blueprint_id=blueprint.id,
            recommendation_id=blueprint.recommendation_id,
            semantic_fingerprint=blueprint.semantic_fingerprint,
            skill_family=blueprint.skill_family,
            package_name=blueprint.name,
            registry_key=blueprint.semantic_fingerprint,
            installed_location=installation.installed_location,
            registration_status="registered",
        )
        # Append-only — never overwrite a prior entry, even on duplicate key.
        self._entries.append(entry)
        return entry

    def entries(self) -> List[RegistryEntry]:
        return list(self._entries)  # copy — callers can't mutate internals

    def get(self, registry_key: str) -> Optional[RegistryEntry]:
        # Most-recently appended entry wins (supersession without overwrite).
        for entry in reversed(self._entries):
            if entry.registry_key == registry_key:
                return entry
        return None
