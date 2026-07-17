"""
brain/skills/registry.py — Phase 5.2 SkillRegistry

Metadata storage and discovery ONLY. Never loads or runs code; never
references implementations beyond the provider metadata on SkillSpec.

Thread-safe (mirrors SessionManager's lock discipline).
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from brain.skills.models import SkillSpec


class SkillRegistry:
    """In-memory skill metadata registry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._specs: Dict[str, SkillSpec] = {}

    def register(self, spec: SkillSpec) -> None:
        """Register a SkillSpec. Duplicate ids raise — one owner per id."""
        with self._lock:
            if spec.id in self._specs:
                raise ValueError(f"[SkillRegistry] Skill '{spec.id}' is already registered.")
            self._specs[spec.id] = spec

    def get(self, skill_id: str) -> Optional[SkillSpec]:
        """Return the SkillSpec for *skill_id*, or None."""
        return self._specs.get(skill_id)

    def find(self, query: str = "", tags: Optional[List[str]] = None) -> List[SkillSpec]:
        """
        Discover skills by free-text query and/or tags.

        - query: case-insensitive substring match on id/name/description.
        - tags:  spec must carry ALL given tags.
        Both empty → all specs.
        """
        q = (query or "").strip().lower()
        wanted = set(tags or [])
        results: List[SkillSpec] = []
        for spec in self._specs.values():
            if q and q not in f"{spec.id} {spec.name} {spec.description}".lower():
                continue
            if wanted and not wanted.issubset(set(spec.tags)):
                continue
            results.append(spec)
        return results

    def all(self) -> List[SkillSpec]:
        """Return every registered SkillSpec."""
        return list(self._specs.values())

    def __len__(self) -> int:
        return len(self._specs)
