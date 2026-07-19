"""
brain/skills/interfaces.py — Phase 5.5 Step 1: skill-layer contract

ISkillRegistry: the metadata storage + discovery contract. Behaviour only,
no implementation details. Defined here as the target-architecture home for
skill-layer interfaces; SkillRegistry (registry.py) implements it.

No consumer resolves this interface yet — introduced as foundation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from brain.skills.models import SkillSpec
from brain.skills.metadata import SkillMetadata


class ISkillRegistry(ABC):
    """Metadata storage and discovery contract for the skill layer."""

    @abstractmethod
    def register(self, spec: SkillSpec, source: str = "builtin") -> None:
        """Register a SkillSpec with an optional origin source. Duplicate ids raise."""

    @abstractmethod
    def get(self, skill_id: str) -> Optional[SkillSpec]:
        """Return the SkillSpec for *skill_id*, or None."""

    @abstractmethod
    def find(self, query: str = "", tags: Optional[List[str]] = None) -> List[SkillSpec]:
        """Discover skills by free-text query and/or tags."""

    @abstractmethod
    def all(self) -> List[SkillSpec]:
        """Return every registered SkillSpec."""

    @abstractmethod
    def get_metadata(self, skill_id: str) -> Optional[SkillMetadata]:
        """Return the SkillMetadata for *skill_id*, or None (Phase 5.5)."""

    @abstractmethod
    def all_metadata(self) -> List[SkillMetadata]:
        """Return metadata for every registered skill (Phase 5.5)."""

    @abstractmethod
    def search(
        self,
        *,
        category: Optional[str] = None,
        permission: Optional[str] = None,
        tags: Optional[List[str]] = None,
        confirmation_required: Optional[bool] = None,
        inputs: Optional[List[str]] = None,
        outputs: Optional[List[str]] = None,
        source: Optional[str] = None,
    ) -> List[SkillMetadata]:
        """Capability discovery over metadata (Phase 5.5 Step 2). Read-only,
        deterministic, registration-order preserving; None filters ignored.
        source filter added in Step 5 (None => all sources)."""
