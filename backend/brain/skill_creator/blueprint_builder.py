"""
brain/skill_creator/blueprint_builder.py — Phase 7.2: BlueprintBuilder

Deterministic transformer: EvolutionRecommendationSet (Phase 6 output) →
SkillBlueprintSet (descriptive metadata). Implements ISkillCreator.

It generates NO code, writes NO files, edits NO prompts, installs NO skills,
updates NO registries, touches NO runtime, and activates nothing. Each
recommendation maps to zero or one blueprint via a fixed rule table. No LLM, no
randomness, no timestamps, no UUID, no hashes — same input yields byte-identical
output. Read-only over the input (frozen models; never mutated).

Depends ONLY on brain.skill_creator.models, brain.skill_creator.interfaces,
brain.evolution.models, typing, pydantic.
"""

from __future__ import annotations

from typing import Optional

from brain.evolution.models import EvolutionRecommendation, EvolutionRecommendationSet
from brain.skill_creator.interfaces import ISkillCreator
from brain.skill_creator.models import (
    SkillBlueprint,
    SkillBlueprintSet,
    MarketplaceIdentity,
)

_SCHEMA_VERSION = "1.0"
_PHASE = "7.2"

# Deterministic mapping: recommendation kind -> blueprint skill kind.
# Kinds not present here produce NO blueprint (e.g. observe_more, keep_strategy).
_KIND_MAP = {
    "improve_strategy": "strategy_optimizer",
    "merge_memory": "memory_consolidation",
    "future_skill_candidate": "new_skill",
}

# Deterministic Skill DNA (lowercase semantic tags) per skill kind.
_DNA_MAP = {
    "strategy_optimizer": ("strategy", "optimization"),
    "memory_consolidation": ("memory", "consolidation"),
    "new_skill": ("skill", "candidate"),
}

# Deterministic skill family per skill kind (sibling grouping — metadata only).
_FAMILY_MAP = {
    "strategy_optimizer": "planner.strategy",
    "memory_consolidation": "workspace.memory",
    "new_skill": "skill.candidate",
}

# Deterministic engineering-complexity per skill kind (rule-based, no calc).
_COMPLEXITY_MAP = {
    "strategy_optimizer": "medium",
    "memory_consolidation": "small",
    "new_skill": "large",
}

# Deterministic risk-profile flags per skill kind (booleans only).
_RISK_MAP = {
    "strategy_optimizer": {"workspace": True},
    "memory_consolidation": {"memory": True},
    "new_skill": {},
}

# Deterministic human-summary templates keyed by skill kind.
_SUMMARY_TEMPLATES = {
    "strategy_optimizer": (
        "Lumina proposes a strategy_optimizer skill because strategy "
        "'{target}' is underperforming and could be improved."
    ),
    "memory_consolidation": (
        "Lumina proposes a memory_consolidation skill because duplicate "
        "memory records ({target}) can be merged."
    ),
    "new_skill": (
        "Lumina proposes a new skill for '{target}' identified as a future "
        "capability candidate."
    ),
}


class BlueprintBuilder(ISkillCreator):
    """Deterministic EvolutionRecommendationSet -> SkillBlueprintSet transformer."""

    def create_blueprint(
        self, recommendations: EvolutionRecommendationSet
    ) -> SkillBlueprintSet:
        blueprints = []
        for rec in recommendations.recommendations:
            bp = self._blueprint_for(rec)
            if bp is not None:
                blueprints.append(bp)
        return SkillBlueprintSet(
            blueprints=blueprints,
            blueprint_count=len(blueprints),
        )

    # ---- pure helpers -------------------------------------------------

    def _blueprint_for(
        self, rec: EvolutionRecommendation
    ) -> Optional[SkillBlueprint]:
        skill_kind = _KIND_MAP.get(rec.kind)
        if skill_kind is None:
            return None  # no blueprint for this recommendation kind

        target = rec.target or "unspecified"
        # Deterministic id: bp:<skill_kind>:<target>.
        blueprint_id = f"bp:{skill_kind}:{target}"

        summary = _SUMMARY_TEMPLATES[skill_kind].format(target=target)

        provenance = {
            "recommendation_id": rec.id,
            "phase": _PHASE,
            "generated_by": "BlueprintBuilder",
            "schema_version": _SCHEMA_VERSION,
        }

        skill_dna = _DNA_MAP[skill_kind]
        complexity = _COMPLEXITY_MAP[skill_kind]
        risk_profile = self._risk_profile(skill_kind)
        family = _FAMILY_MAP[skill_kind]

        # Semantic fingerprint: deterministic semantic identity (NOT a hash,
        # checksum, or UUID). Stable dotted form <family>.<target>.v1 — later
        # phases use it for duplicate detection / semantic reuse.
        semantic_fingerprint = f"{family}.{target}.v1"

        # Deterministic marketplace identity (declaration only — no networking).
        marketplace_identity = MarketplaceIdentity(
            exportable_identity=semantic_fingerprint,
            marketplace_tags=skill_dna,
            compatibility_family=family,
            semantic_version_strategy="semver",
        )

        # Canonical signature: deterministic metadata representation (NOT a hash,
        # NOT a checksum, NOT a UUID). A stable ordered join of identity fields.
        canonical_signature = "|".join([
            f"schema={_SCHEMA_VERSION}",
            f"kind={skill_kind}",
            f"target={target}",
            f"rec={rec.id}",
            f"dna={'.'.join(skill_dna)}",
        ])

        return SkillBlueprint(
            id=blueprint_id,
            recommendation_id=rec.id,
            blueprint_schema_version=_SCHEMA_VERSION,
            canonical_signature=canonical_signature,
            name=f"{skill_kind}:{target}",
            description=rec.reason,
            purpose=rec.kind,
            skill_kind=skill_kind,
            skill_family=family,
            semantic_fingerprint=semantic_fingerprint,
            human_summary=summary,
            source_recommendation_ids=[rec.id],
            skill_dna=skill_dna,
            provided_capabilities=[skill_kind],
            required_capabilities=list(rec.related_ids),
            status="draft",
            approval_required=True,
            engineering_complexity=complexity,
            confidence=rec.confidence,
            risk_profile=risk_profile,
            rollback_strategy="remove_generated_skill",
            marketplace_identity=marketplace_identity,
            provenance=provenance,
        )

    @staticmethod
    def _risk_profile(skill_kind: str) -> dict:
        """Deterministic boolean risk flags for *skill_kind* (metadata only)."""
        base = {
            "filesystem": False,
            "network": False,
            "shell": False,
            "workspace": False,
            "memory": False,
        }
        base.update(_RISK_MAP.get(skill_kind, {}))
        return base
