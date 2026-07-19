"""
brain/skills/registry.py — SkillRegistry (Phase 5.5 Step 1: metadata layer)

Metadata storage and discovery ONLY. Never loads or runs code; never
references implementations beyond the provider metadata on SkillSpec.

Phase 5.5: every registered SkillSpec also gets a derived, immutable
SkillMetadata stored alongside it (get_metadata / all_metadata). SkillSpec
remains the execution-path contract; the registration API is unchanged.

Thread-safe (mirrors SessionManager's lock discipline).
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from brain.skills.models import SkillSpec
from brain.skills.metadata import SkillMetadata
from brain.skills.interfaces import ISkillRegistry
from brain.skills.sources import DEFAULT_SOURCE


class SkillRegistry(ISkillRegistry):
    """In-memory skill metadata registry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._specs: Dict[str, SkillSpec] = {}
        self._metadata: Dict[str, SkillMetadata] = {}

    def register(self, spec: SkillSpec, source: str = DEFAULT_SOURCE) -> None:
        """
        Register a SkillSpec. Duplicate ids raise — one owner per id.

        Phase 5.5: also derives and stores a SkillMetadata for the spec.

        Phase 5.5 Step 5: *source* records the skill's origin (builtin/plugin/
        mcp/generated/remote). Optional and defaults to "builtin", so existing
        register(spec) calls are unchanged. The planner receives identical
        SkillMetadata regardless of source.
        """
        with self._lock:
            if spec.id in self._specs:
                raise ValueError(f"[SkillRegistry] Skill '{spec.id}' is already registered.")
            self._specs[spec.id] = spec
            self._metadata[spec.id] = SkillMetadata.from_spec(spec, source=source)

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

    def get_metadata(self, skill_id: str) -> Optional[SkillMetadata]:
        """Return the derived SkillMetadata for *skill_id*, or None (Phase 5.5)."""
        return self._metadata.get(skill_id)

    def all_metadata(self) -> List[SkillMetadata]:
        """Return derived metadata for every registered skill (Phase 5.5)."""
        return list(self._metadata.values())

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
        """
        Capability discovery over SkillMetadata (Phase 5.5 Step 2).

        Read-only, passive, deterministic. Results preserve registration
        order. Each filter that is None is ignored. Matching rules:
          - category               exact match
          - permission             metadata.permissions contains it
          - tags                   metadata.tags contains ALL requested
          - inputs                 metadata.inputs contains ALL requested
          - outputs                metadata.outputs contains ALL requested
          - confirmation_required  exact bool match
          - source                 exact match (Step 5). None => all sources.
        """
        want_tags = set(tags or [])
        want_inputs = set(inputs or [])
        want_outputs = set(outputs or [])

        results: List[SkillMetadata] = []
        for md in self._metadata.values():  # dict preserves insertion order
            if category is not None and md.category != category:
                continue
            if permission is not None and permission not in md.permissions:
                continue
            if want_tags and not want_tags.issubset(set(md.tags)):
                continue
            if want_inputs and not want_inputs.issubset(set(md.inputs)):
                continue
            if want_outputs and not want_outputs.issubset(set(md.outputs)):
                continue
            if confirmation_required is not None and \
                    md.confirmation_required != confirmation_required:
                continue
            if source is not None and md.source != source:
                continue
            results.append(md)
        return results

    def __len__(self) -> int:
        return len(self._specs)
