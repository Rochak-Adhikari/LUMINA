"""
tests/test_phase_7_step2_5.py — Milestone 7.2.5 Verification (Blueprint Schema Hardening)

Architecture-only schema expansion. Verifies the hardened SkillBlueprint:

  - Skill DNA (frozen tuple, lowercase, max 8)
  - runtime compatibility fields (minimum_runtime_version / minimum_api_version)
  - documentation + changelog reservations
  - engineering complexity restricted to small/medium/large
  - generation cost estimate defaults
  - structured risk_profile (boolean flags)
  - canonical permission vocabulary restricted (Literal)
  - canonical_signature deterministic (not a hash)
  - expanded lifecycle restricted
  - frozen, serializable, byte-identical repeat construction

Stdlib unittest; no heavy deps.
"""

import unittest
from pathlib import Path
import sys

import pydantic

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import EvolutionRecommendation, EvolutionRecommendationSet
from brain.skill_creator.models import SkillBlueprint
from brain.skill_creator.blueprint_builder import BlueprintBuilder


def _bp(**kw):
    base = dict(id="bp:x", recommendation_id="r1")
    base.update(kw)
    return SkillBlueprint(**base)


def _built(kind="improve_strategy", target="seq", related=None):
    rec = EvolutionRecommendation(
        id="r1", kind=kind, target=target, confidence=0.5, related_ids=list(related or [])
    )
    s = EvolutionRecommendationSet(recommendations=[rec], recommendation_count=1)
    return BlueprintBuilder().create_blueprint(s).blueprints[0]


class TestSchemaDefaults(unittest.TestCase):
    def test_skill_dna_default_empty_tuple(self):
        self.assertEqual(_bp().skill_dna, ())

    def test_skill_dna_is_tuple(self):
        bp = _bp(skill_dna=("workspace", "reasoning"))
        self.assertIsInstance(bp.skill_dna, tuple)

    def test_compatibility_defaults(self):
        bp = _bp()
        self.assertEqual(bp.minimum_runtime_version, "2.6.0")
        self.assertEqual(bp.minimum_api_version, "1.0")

    def test_documentation_default(self):
        self.assertEqual(_bp().documentation,
                         {"readme": True, "examples": True, "developer_notes": False})

    def test_changelog_default(self):
        self.assertTrue(_bp().include_changelog)

    def test_risk_profile_default_all_false(self):
        rp = _bp().risk_profile
        self.assertEqual(set(rp), {"filesystem", "network", "shell", "workspace", "memory"})
        self.assertFalse(any(rp.values()))

    def test_generation_estimate_defaults(self):
        bp = _bp()
        self.assertEqual(bp.estimated_generation_tokens, 0)
        self.assertEqual(bp.estimated_generation_steps, 0)

    def test_engineering_complexity_default(self):
        self.assertEqual(_bp().engineering_complexity, "small")


class TestRestrictedVocabulary(unittest.TestCase):
    def test_complexity_restricted(self):
        _bp(engineering_complexity="large")  # ok
        with self.assertRaises(pydantic.ValidationError):
            _bp(engineering_complexity="huge")

    def test_permissions_restricted(self):
        _bp(required_permissions=["filesystem.read", "network.http"])  # ok
        with self.assertRaises(pydantic.ValidationError):
            _bp(required_permissions=["do.anything"])

    def test_lifecycle_restricted(self):
        for s in ["draft", "validated", "generated", "tested", "approved",
                  "installed", "deprecated", "retired"]:
            _bp(status=s)
        with self.assertRaises(pydantic.ValidationError):
            _bp(status="active")  # removed value


class TestImmutability(unittest.TestCase):
    def test_frozen(self):
        bp = _bp(skill_dna=("a",))
        for attr, val in [("skill_dna", ("b",)), ("minimum_api_version", "2.0"),
                          ("documentation", {}), ("risk_profile", {})]:
            with self.assertRaises(Exception):
                setattr(bp, attr, val)

    def test_serializable(self):
        import json
        json.dumps(_bp(skill_dna=("workspace", "reasoning")).model_dump())

    def test_byte_identical_repeat(self):
        self.assertEqual(_bp().model_dump(), _bp().model_dump())


class TestBuilderPopulation(unittest.TestCase):
    def test_dna_populated(self):
        self.assertEqual(_built("improve_strategy").skill_dna, ("strategy", "optimization"))
        self.assertEqual(_built("merge_memory", "n").skill_dna, ("memory", "consolidation"))

    def test_complexity_populated(self):
        self.assertEqual(_built("improve_strategy").engineering_complexity, "medium")
        self.assertEqual(_built("merge_memory", "n").engineering_complexity, "small")
        self.assertEqual(_built("future_skill_candidate", "w").engineering_complexity, "large")

    def test_risk_profile_populated(self):
        self.assertTrue(_built("improve_strategy").risk_profile["workspace"])
        self.assertTrue(_built("merge_memory", "n").risk_profile["memory"])

    def test_canonical_signature_deterministic(self):
        a = _built("improve_strategy", "seq")
        b = _built("improve_strategy", "seq")
        self.assertEqual(a.canonical_signature, b.canonical_signature)
        self.assertIn("kind=strategy_optimizer", a.canonical_signature)
        self.assertIn("target=seq", a.canonical_signature)
        # not a hash: human-readable, contains field markers
        self.assertIn("schema=1.0", a.canonical_signature)

    def test_semantic_fingerprint_deterministic(self):
        a = _built("merge_memory", "notes")
        b = _built("merge_memory", "notes")
        self.assertEqual(a.semantic_fingerprint, b.semantic_fingerprint)
        # semantic identity form <family>.<target>.v1, not a hash
        self.assertEqual(a.semantic_fingerprint, "workspace.memory.notes.v1")

    def test_skill_family_deterministic(self):
        self.assertEqual(_built("improve_strategy").skill_family, "planner.strategy")
        self.assertEqual(_built("merge_memory", "n").skill_family, "workspace.memory")
        self.assertEqual(_built("future_skill_candidate", "w").skill_family, "skill.candidate")

    def test_seed_fields_default_empty(self):
        self.assertEqual(_bp().semantic_fingerprint, "")
        self.assertEqual(_bp().skill_family, "")

    def test_builder_byte_identical(self):
        self.assertEqual(_built().model_dump(), _built().model_dump())


if __name__ == "__main__":
    unittest.main()
