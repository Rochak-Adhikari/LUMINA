"""
brain/skill_creator/blueprint_generator.py — Phase 7.4: BlueprintGenerator

Pipeline stage 03 (Generation). Consumes ONE verified SkillBlueprint plus its
VerificationResult and produces ONE immutable GenerationResult describing the
skill package's files (relative path -> content string).

Gated: generation only proceeds when verification.passed is True; otherwise it
returns an ungenerated result with a skipped_reason. It NEVER writes to disk,
installs, activates, or executes anything — it only records WHAT would be
written. (Writing is installation, stage 06.)

Deterministic: pure function of (blueprint, verification). File contents are
built from fixed templates + the blueprint's frozen fields. No UUID, timestamps,
randomness, hashing, filesystem, network, or LLM. Same inputs -> byte-identical
GenerationResult.

Depends only on brain.skill_creator.models, brain.skill_creator.interfaces,
json, typing.
"""

from __future__ import annotations

import json
from typing import Dict

from brain.skill_creator.interfaces import IBlueprintGenerator
from brain.skill_creator.models import (
    SkillBlueprint,
    VerificationResult,
    GenerationResult,
)


class BlueprintGenerator(IBlueprintGenerator):
    """Deterministic package descriptor generator for a verified blueprint."""

    def generate(
        self, blueprint: SkillBlueprint, verification: VerificationResult
    ) -> GenerationResult:
        # Gate: never generate from an unverified / failed blueprint.
        if not verification.passed:
            return GenerationResult(
                blueprint_id=blueprint.id,
                recommendation_id=blueprint.recommendation_id,
                generated=False,
                skipped_reason="verification_failed",
            )

        layout = blueprint.package_layout
        files: Dict[str, str] = {}

        # manifest.json — deterministic package manifest.
        files[layout["manifest"]] = self._json({
            "name": blueprint.name,
            "skill_kind": blueprint.skill_kind,
            "skill_family": blueprint.skill_family,
            "semantic_fingerprint": blueprint.semantic_fingerprint,
            "manifest_version": blueprint.generation_contract.expected_manifest_version,
            "provided_capabilities": list(blueprint.provided_capabilities),
            "required_capabilities": list(blueprint.required_capabilities),
            "required_permissions": list(blueprint.required_permissions),
            "approval_required": blueprint.approval_required,
        })

        # metadata.json — descriptive blueprint metadata.
        files[layout["metadata"]] = self._json({
            "blueprint_id": blueprint.id,
            "recommendation_id": blueprint.recommendation_id,
            "purpose": blueprint.purpose,
            "engineering_complexity": blueprint.engineering_complexity,
            "risk_profile": dict(blueprint.risk_profile),
            "skill_dna": list(blueprint.skill_dna),
        })

        # provenance.json — audit trail (already deterministic on the blueprint).
        files[layout["provenance"]] = self._json(dict(blueprint.provenance))

        # README.md — deterministic human-readable summary.
        files[layout["readme"]] = (
            f"# {blueprint.name}\n\n{blueprint.human_summary}\n\n"
            f"- Kind: {blueprint.skill_kind}\n"
            f"- Family: {blueprint.skill_family}\n"
            f"- Fingerprint: {blueprint.semantic_fingerprint}\n"
        )

        # skill.py — inert scaffold. This is descriptive text recorded in the
        # result, NOT executed here. A future generation milestone may enrich it.
        files[layout["implementation"]] = (
            f'"""Generated skill scaffold for {blueprint.name}.\n'
            f'{blueprint.human_summary}\n"""\n\n\n'
            f"class Skill:\n"
            f"    skill_kind = {blueprint.skill_kind!r}\n"
            f"    semantic_fingerprint = {blueprint.semantic_fingerprint!r}\n\n"
            f"    def run(self, *args, **kwargs):\n"
            f"        raise NotImplementedError('scaffold only')\n"
        )

        # tests.py — inert test scaffold placeholder.
        files[layout["tests"]] = (
            f'"""Generated test scaffold for {blueprint.name}."""\n\n\n'
            f"def test_placeholder():\n"
            f"    assert True\n"
        )

        return GenerationResult(
            blueprint_id=blueprint.id,
            recommendation_id=blueprint.recommendation_id,
            generated=True,
            package_name=blueprint.name,
            manifest_version=blueprint.generation_contract.expected_manifest_version,
            files=files,
        )

    @staticmethod
    def _json(obj) -> str:
        """Deterministic JSON: sorted keys, stable separators (no whitespace drift)."""
        return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False)
