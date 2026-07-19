"""
brain/skills/resolver.py — Phase 5.5 Step 4: Capability Ranking

CapabilityResolver owns deterministic capability ranking. It sits between
SkillRegistry discovery and Task.skill_id selection. No ranking logic lives
in the planner, the registry, or the manager.

Deterministic ONLY — no embeddings, vectors, cosine similarity, AI/LLM,
randomness, confidence models, or ML. The same inputs always produce the
same ranking and the same winner.

Scoring (reference weights; deterministic):
  category match            +50
  permission match          +20
  each matching tag         +10
  each matching input        +5
  each matching output       +5
  confirmation flag matches  +5
  origin preference          +0  (none yet)
  version preference         +0  (none yet)

Tie-break: equal score → the earlier-registered skill wins (stable order),
never random.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from brain.skills.metadata import SkillMetadata

# Reference weights (adjustable; algorithm stays deterministic).
_W_CATEGORY = 50
_W_PERMISSION = 20
_W_TAG = 10
_W_INPUT = 5
_W_OUTPUT = 5
_W_CONFIRMATION = 5


class CapabilityResolver:
    """Deterministic ranking over SkillMetadata."""

    def __init__(self, registry: Any) -> None:
        self._registry = registry

    def score(
        self,
        md: SkillMetadata,
        *,
        category: Optional[str] = None,
        permission: Optional[str] = None,
        tags: Optional[List[str]] = None,
        inputs: Optional[List[str]] = None,
        outputs: Optional[List[str]] = None,
        confirmation_required: Optional[bool] = None,
    ) -> int:
        """Deterministic additive score of *md* against the requested signals.
        Each None signal contributes nothing."""
        total = 0
        if category is not None and md.category == category:
            total += _W_CATEGORY
        if permission is not None and permission in md.permissions:
            total += _W_PERMISSION
        if tags:
            total += _W_TAG * len(set(tags) & set(md.tags))
        if inputs:
            total += _W_INPUT * len(set(inputs) & set(md.inputs))
        if outputs:
            total += _W_OUTPUT * len(set(outputs) & set(md.outputs))
        if confirmation_required is not None and \
                md.confirmation_required == confirmation_required:
            total += _W_CONFIRMATION
        return total

    def rank(
        self,
        candidates: List[SkillMetadata],
        *,
        category: Optional[str] = None,
        permission: Optional[str] = None,
        tags: Optional[List[str]] = None,
        inputs: Optional[List[str]] = None,
        outputs: Optional[List[str]] = None,
        confirmation_required: Optional[bool] = None,
    ) -> List[SkillMetadata]:
        """
        Return *candidates* ordered by score (desc), ties broken by the
        original position (earlier-registered wins). Stable and deterministic.
        Candidates that score 0 are retained (caller decides the threshold).
        """
        scored: List[Tuple[int, int, SkillMetadata]] = []
        for idx, md in enumerate(candidates):
            s = self.score(
                md, category=category, permission=permission, tags=tags,
                inputs=inputs, outputs=outputs,
                confirmation_required=confirmation_required,
            )
            scored.append((s, idx, md))
        # -score for descending; idx ascending as the deterministic tie-break.
        scored.sort(key=lambda t: (-t[0], t[1]))
        return [md for _, _, md in scored]

    def resolve(
        self,
        *,
        category: Optional[str] = None,
        permission: Optional[str] = None,
        tags: Optional[List[str]] = None,
        inputs: Optional[List[str]] = None,
        outputs: Optional[List[str]] = None,
        confirmation_required: Optional[bool] = None,
    ) -> Optional[SkillMetadata]:
        """
        Rank all registered skills against the signals and return the single
        best SkillMetadata, or None when nothing scores above zero (no
        relevant capability). Registration order breaks ties.
        """
        try:
            candidates = self._registry.all_metadata()
        except Exception:
            return None
        if not candidates:
            return None
        ranked = self.rank(
            candidates, category=category, permission=permission, tags=tags,
            inputs=inputs, outputs=outputs,
            confirmation_required=confirmation_required,
        )
        best = ranked[0]
        if self.score(
            best, category=category, permission=permission, tags=tags,
            inputs=inputs, outputs=outputs,
            confirmation_required=confirmation_required,
        ) <= 0:
            return None
        return best
