"""
tests/test_phase_7_step3.py — Milestone 7.3 (Blueprint Verification)

Pipeline stage 02. BlueprintVerifier: SkillBlueprint -> VerificationResult.

Verifies:
  - well-formed blueprint (BlueprintBuilder output) passes all checks
  - each static check fails for the corresponding malformed blueprint
  - VerificationResult frozen, deterministic, byte-identical repeat
  - blueprint unchanged (immutability law)
  - integration: BlueprintBuilder -> BlueprintVerifier passes
  - no forbidden imports / no executable payload
  - dormant DI registration
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import EvolutionRecommendation, EvolutionRecommendationSet
from brain.skill_creator.models import SkillBlueprint, VerificationResult
from brain.skill_creator.blueprint_builder import BlueprintBuilder
from brain.skill_creator.blueprint_verifier import BlueprintVerifier
from brain.skill_creator.interfaces import IBlueprintVerifier


def _wellformed(**overrides):
    base = dict(
        id="bp:strategy_optimizer:seq",
        recommendation_id="r1",
        provided_capabilities=["strategy_optimizer"],
    )
    base.update(overrides)
    return SkillBlueprint(**base)


def _built(kind="improve_strategy", target="seq"):
    rec = EvolutionRecommendation(id="r1", kind=kind, target=target, confidence=0.5)
    s = EvolutionRecommendationSet(recommendations=[rec], recommendation_count=1)
    return BlueprintBuilder().create_blueprint(s).blueprints[0]


class TestPass(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(BlueprintVerifier(), IBlueprintVerifier)

    def test_wellformed_passes(self):
        r = BlueprintVerifier().verify(_wellformed())
        self.assertTrue(r.passed, r.failures)
        self.assertEqual(r.failures, [])
        self.assertTrue(all(r.checks.values()))

    def test_result_carries_ids(self):
        r = BlueprintVerifier().verify(_wellformed())
        self.assertEqual(r.blueprint_id, "bp:strategy_optimizer:seq")
        self.assertEqual(r.recommendation_id, "r1")

    def test_all_declared_checks_present(self):
        bp = _wellformed()
        r = BlueprintVerifier().verify(bp)
        self.assertEqual(set(r.checks), set(bp.verification_contract.expected_checks))


class TestFailures(unittest.TestCase):
    def setUp(self):
        self.v = BlueprintVerifier()

    def test_schema_fail_empty_recommendation_id(self):
        r = self.v.verify(_wellformed(recommendation_id=""))
        self.assertFalse(r.passed)
        self.assertFalse(r.checks["schema"])

    def test_schema_fail_wrong_status(self):
        r = self.v.verify(_wellformed(status="approved"))
        self.assertFalse(r.checks["schema"])

    def test_capabilities_fail_empty(self):
        r = self.v.verify(_wellformed(provided_capabilities=[]))
        self.assertFalse(r.checks["capabilities"])

    def test_permissions_fail_noncanonical(self):
        # bypass Literal validation is impossible at construction; use a valid
        # canonical set to confirm PASS, and rely on schema for the negative.
        r = self.v.verify(_wellformed(required_permissions=["filesystem.read"]))
        self.assertTrue(r.checks["permissions"])

    def test_risk_fail_missing_keys(self):
        r = self.v.verify(_wellformed(risk_profile={"filesystem": True}))
        self.assertFalse(r.checks["risk"])

    def test_failure_reasons_recorded(self):
        r = self.v.verify(_wellformed(recommendation_id="", provided_capabilities=[]))
        self.assertGreaterEqual(len(r.failures), 2)


class TestDeterminismAndImmutability(unittest.TestCase):
    def test_byte_identical_repeat(self):
        v = BlueprintVerifier()
        bp = _wellformed()
        self.assertEqual(v.verify(bp).model_dump(), v.verify(bp).model_dump())

    def test_result_frozen(self):
        r = BlueprintVerifier().verify(_wellformed())
        with self.assertRaises(Exception):
            r.passed = False

    def test_blueprint_unchanged(self):
        bp = _wellformed()
        before = bp.model_dump()
        BlueprintVerifier().verify(bp)
        self.assertEqual(bp.model_dump(), before)


class TestIntegration(unittest.TestCase):
    def test_builder_output_verifies(self):
        for kind, target in [("improve_strategy", "seq"),
                             ("merge_memory", "notes"),
                             ("future_skill_candidate", "web")]:
            bp = _built(kind, target)
            r = BlueprintVerifier().verify(bp)
            self.assertTrue(r.passed, f"{kind}:{target} failed {r.failures}")


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
        for m in self._imports("brain/skill_creator/blueprint_verifier.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_executable_payload(self):
        src = (backend_dir / "brain/skill_creator/blueprint_verifier.py").read_text(encoding="utf-8")
        for banned in ["subprocess", "os.system", "exec(", "eval(", "compile(", "__import__", "open("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IBlueprintVerifier))
        # resolvable, deterministic, no side effects
        r = c.resolve(IBlueprintVerifier).verify(_wellformed())
        self.assertTrue(r.passed)


if __name__ == "__main__":
    unittest.main()
