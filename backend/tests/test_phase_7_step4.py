"""
tests/test_phase_7_step4.py — Milestone 7.4 (Blueprint Generation)

Pipeline stage 03. BlueprintGenerator: (SkillBlueprint, VerificationResult)
-> GenerationResult.

Verifies:
  - gated: failed verification -> generated=False, no files, skipped_reason
  - passing verification -> generated=True with package files
  - files keyed by the blueprint's package_layout
  - manifest/metadata/provenance are valid deterministic JSON
  - GenerationResult frozen, byte-identical repeat
  - inputs unchanged (immutability law)
  - integration: builder -> verifier -> generator
  - no filesystem/exec; allowed imports only
  - dormant DI registration
"""

import ast
import json
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import EvolutionRecommendation, EvolutionRecommendationSet
from brain.skill_creator.models import SkillBlueprint, VerificationResult, GenerationResult
from brain.skill_creator.blueprint_builder import BlueprintBuilder
from brain.skill_creator.blueprint_verifier import BlueprintVerifier
from brain.skill_creator.blueprint_generator import BlueprintGenerator
from brain.skill_creator.interfaces import IBlueprintGenerator


def _built(kind="improve_strategy", target="seq"):
    rec = EvolutionRecommendation(id="r1", kind=kind, target=target, confidence=0.5)
    s = EvolutionRecommendationSet(recommendations=[rec], recommendation_count=1)
    return BlueprintBuilder().create_blueprint(s).blueprints[0]


def _pass(bp):
    return BlueprintVerifier().verify(bp)


def _fail(bp):
    return VerificationResult(blueprint_id=bp.id, recommendation_id=bp.recommendation_id,
                              passed=False, checks={"schema": False}, failures=["x"])


class TestGate(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(BlueprintGenerator(), IBlueprintGenerator)

    def test_failed_verification_skips(self):
        bp = _built()
        r = BlueprintGenerator().generate(bp, _fail(bp))
        self.assertFalse(r.generated)
        self.assertEqual(r.files, {})
        self.assertEqual(r.skipped_reason, "verification_failed")

    def test_passing_generates(self):
        bp = _built()
        r = BlueprintGenerator().generate(bp, _pass(bp))
        self.assertTrue(r.generated)
        self.assertTrue(r.files)
        self.assertEqual(r.package_name, bp.name)


class TestFiles(unittest.TestCase):
    def setUp(self):
        self.bp = _built("merge_memory", "notes")
        self.r = BlueprintGenerator().generate(self.bp, _pass(self.bp))

    def test_files_match_package_layout(self):
        self.assertEqual(set(self.r.files), set(self.bp.package_layout.values()))

    def test_manifest_is_valid_json(self):
        manifest = json.loads(self.r.files["manifest.json"])
        self.assertEqual(manifest["skill_kind"], "memory_consolidation")
        self.assertTrue(manifest["approval_required"])

    def test_metadata_is_valid_json(self):
        meta = json.loads(self.r.files["metadata.json"])
        self.assertEqual(meta["blueprint_id"], self.bp.id)

    def test_provenance_is_valid_json(self):
        prov = json.loads(self.r.files["provenance.json"])
        self.assertEqual(prov["recommendation_id"], "r1")

    def test_skill_scaffold_is_inert(self):
        skill = self.r.files["skill.py"]
        self.assertIn("NotImplementedError", skill)
        self.assertIn("class Skill", skill)


class TestDeterminismImmutability(unittest.TestCase):
    def test_byte_identical_repeat(self):
        bp = _built()
        v = _pass(bp)
        g = BlueprintGenerator()
        self.assertEqual(g.generate(bp, v).model_dump(), g.generate(bp, v).model_dump())

    def test_result_frozen(self):
        bp = _built()
        r = BlueprintGenerator().generate(bp, _pass(bp))
        with self.assertRaises(Exception):
            r.generated = False

    def test_inputs_unchanged(self):
        bp = _built()
        v = _pass(bp)
        bpb, vb = bp.model_dump(), v.model_dump()
        BlueprintGenerator().generate(bp, v)
        self.assertEqual(bp.model_dump(), bpb)
        self.assertEqual(v.model_dump(), vb)


class TestIntegration(unittest.TestCase):
    def test_full_chain(self):
        for kind, target in [("improve_strategy", "seq"),
                             ("merge_memory", "notes"),
                             ("future_skill_candidate", "web")]:
            bp = _built(kind, target)
            v = BlueprintVerifier().verify(bp)
            self.assertTrue(v.passed)
            g = BlueprintGenerator().generate(bp, v)
            self.assertTrue(g.generated, f"{kind}:{target}")
            self.assertEqual(set(g.files), set(bp.package_layout.values()))


class TestBoundaries(unittest.TestCase):
    def _imports(self, rel):
        src = (backend_dir / rel).read_text(encoding="utf-8")
        modules = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                modules.update(a.name for a in node.names)
        return modules

    def test_allowed_imports_only(self):
        allowed = (
            "brain.skill_creator.models",
            "brain.skill_creator.interfaces",
            "json", "typing", "__future__",
        )
        for m in self._imports("brain/skill_creator/blueprint_generator.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_filesystem_or_exec(self):
        src = (backend_dir / "brain/skill_creator/blueprint_generator.py").read_text(encoding="utf-8")
        for banned in ["open(", "subprocess", "os.system", "exec(", "eval(", "compile(", "__import__", "Path("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IBlueprintGenerator))
        bp = _built()
        r = c.resolve(IBlueprintGenerator).generate(bp, _pass(bp))
        self.assertTrue(r.generated)


if __name__ == "__main__":
    unittest.main()
