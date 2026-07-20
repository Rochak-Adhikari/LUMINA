"""
tests/test_phase_7_step5.py — Milestone 7.5 (Blueprint Testing)

Pipeline stage 04. BlueprintTester: (SkillBlueprint, GenerationResult)
-> TestResult.

Verifies:
  - gated: not-generated -> tested=False, skipped_reason
  - generated package -> tested=True, all declared categories evaluated
  - unit/determinism/safety categories pass for a clean generated package
  - determinism category fails when impl contains nondeterministic tokens
  - safety category fails when impl contains unsafe tokens
  - TestResult frozen, byte-identical repeat; inputs unchanged
  - integration: builder -> verifier -> generator -> tester
  - no exec/filesystem; allowed imports only; dormant DI
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import EvolutionRecommendation, EvolutionRecommendationSet
from brain.skill_creator.models import GenerationResult, TestResult
from brain.skill_creator.blueprint_builder import BlueprintBuilder
from brain.skill_creator.blueprint_verifier import BlueprintVerifier
from brain.skill_creator.blueprint_generator import BlueprintGenerator
from brain.skill_creator.blueprint_tester import BlueprintTester
from brain.skill_creator.interfaces import IBlueprintTester


def _built(kind="improve_strategy", target="seq"):
    rec = EvolutionRecommendation(id="r1", kind=kind, target=target, confidence=0.5)
    s = EvolutionRecommendationSet(recommendations=[rec], recommendation_count=1)
    return BlueprintBuilder().create_blueprint(s).blueprints[0]


def _gen(bp):
    v = BlueprintVerifier().verify(bp)
    return BlueprintGenerator().generate(bp, v)


def _not_generated(bp):
    return GenerationResult(blueprint_id=bp.id, recommendation_id=bp.recommendation_id,
                            generated=False, skipped_reason="verification_failed")


class TestGate(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(BlueprintTester(), IBlueprintTester)

    def test_not_generated_skips(self):
        bp = _built()
        r = BlueprintTester().test(bp, _not_generated(bp))
        self.assertFalse(r.tested)
        self.assertEqual(r.skipped_reason, "not_generated")

    def test_generated_is_tested(self):
        bp = _built()
        r = BlueprintTester().test(bp, _gen(bp))
        self.assertTrue(r.tested)
        self.assertTrue(r.passed, r.failures)


class TestCategories(unittest.TestCase):
    def setUp(self):
        self.bp = _built()
        self.t = BlueprintTester()

    def test_all_declared_categories(self):
        r = self.t.test(self.bp, _gen(self.bp))
        self.assertEqual(set(r.categories),
                         set(self.bp.verification_contract.required_test_categories))

    def test_clean_package_passes_all(self):
        r = self.t.test(self.bp, _gen(self.bp))
        self.assertTrue(all(r.categories.values()))

    def test_determinism_fails_on_bad_impl(self):
        gen = _gen(self.bp)
        bad = GenerationResult(
            blueprint_id=gen.blueprint_id, recommendation_id=gen.recommendation_id,
            generated=True, package_name=gen.package_name,
            files={**gen.files, self.bp.package_layout["implementation"]: "import random\n"},
        )
        r = self.t.test(self.bp, bad)
        self.assertFalse(r.categories["determinism"])
        self.assertFalse(r.passed)

    def test_safety_fails_on_unsafe_impl(self):
        gen = _gen(self.bp)
        bad = GenerationResult(
            blueprint_id=gen.blueprint_id, recommendation_id=gen.recommendation_id,
            generated=True, package_name=gen.package_name,
            files={**gen.files, self.bp.package_layout["implementation"]: "import subprocess\n"},
        )
        r = self.t.test(self.bp, bad)
        self.assertFalse(r.categories["safety"])

    def test_unit_fails_without_tests(self):
        gen = _gen(self.bp)
        bad = GenerationResult(
            blueprint_id=gen.blueprint_id, recommendation_id=gen.recommendation_id,
            generated=True, package_name=gen.package_name,
            files={**gen.files, self.bp.package_layout["tests"]: ""},
        )
        r = self.t.test(self.bp, bad)
        self.assertFalse(r.categories["unit"])


class TestDeterminismImmutability(unittest.TestCase):
    def test_byte_identical_repeat(self):
        bp = _built()
        g = _gen(bp)
        t = BlueprintTester()
        self.assertEqual(t.test(bp, g).model_dump(), t.test(bp, g).model_dump())

    def test_result_frozen(self):
        bp = _built()
        r = BlueprintTester().test(bp, _gen(bp))
        with self.assertRaises(Exception):
            r.passed = False

    def test_inputs_unchanged(self):
        bp = _built()
        g = _gen(bp)
        bpb, gb = bp.model_dump(), g.model_dump()
        BlueprintTester().test(bp, g)
        self.assertEqual(bp.model_dump(), bpb)
        self.assertEqual(g.model_dump(), gb)


class TestIntegration(unittest.TestCase):
    def test_full_chain(self):
        for kind, target in [("improve_strategy", "seq"),
                             ("merge_memory", "notes"),
                             ("future_skill_candidate", "web")]:
            bp = _built(kind, target)
            v = BlueprintVerifier().verify(bp)
            g = BlueprintGenerator().generate(bp, v)
            r = BlueprintTester().test(bp, g)
            self.assertTrue(r.tested and r.passed, f"{kind}:{target} {r.failures}")


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
            "typing", "__future__",
        )
        for m in self._imports("brain/skill_creator/blueprint_tester.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_exec_or_filesystem(self):
        # The tester inspects file text statically. It must not import os/
        # subprocess/importlib or open files. (Authoritative: AST imports —
        # unsafe tokens legitimately appear as detection strings in the source.)
        modules = self._imports("brain/skill_creator/blueprint_tester.py")
        for banned in ["os", "subprocess", "importlib", "pathlib"]:
            self.assertNotIn(banned, modules, f"forbidden import {banned}")
        src = (backend_dir / "brain/skill_creator/blueprint_tester.py").read_text(encoding="utf-8")
        self.assertNotIn("open(", src)

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IBlueprintTester))
        bp = _built()
        r = c.resolve(IBlueprintTester).test(bp, _gen(bp))
        self.assertTrue(r.passed)


if __name__ == "__main__":
    unittest.main()
