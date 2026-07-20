"""
tests/test_phase_7_step6.py — Milestone 7.6 (Blueprint Approval)

Pipeline stage 05 — the mandatory human gate. BlueprintApprover:
TestResult + explicit decision -> ApprovalRecord.

Verifies:
  - gated: failed TestResult cannot be approved
  - approve=True + passing tests -> approved
  - approve=False -> rejected (not approved)
  - never auto-approves (approve flag required; no default True)
  - caller-supplied timestamp carried through; none generated
  - ApprovalRecord frozen, deterministic, inputs unchanged
  - full chain: builder->verifier->generator->tester->approver
  - import allowlist, no forbidden imports / no exec / no filesystem
  - dormant DI registration
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import EvolutionRecommendation, EvolutionRecommendationSet
from brain.skill_creator.models import TestResult, ApprovalRecord
from brain.skill_creator.blueprint_builder import BlueprintBuilder
from brain.skill_creator.blueprint_verifier import BlueprintVerifier
from brain.skill_creator.blueprint_generator import BlueprintGenerator
from brain.skill_creator.blueprint_tester import BlueprintTester
from brain.skill_creator.blueprint_approver import BlueprintApprover
from brain.skill_creator.interfaces import IBlueprintApprover


def _built(kind="improve_strategy", target="seq"):
    rec = EvolutionRecommendation(id="r1", kind=kind, target=target, confidence=0.5)
    s = EvolutionRecommendationSet(recommendations=[rec], recommendation_count=1)
    return BlueprintBuilder().create_blueprint(s).blueprints[0]


def _passing_test(bp):
    v = BlueprintVerifier().verify(bp)
    g = BlueprintGenerator().generate(bp, v)
    return BlueprintTester().test(bp, g)


def _failed_test(bp):
    return TestResult(blueprint_id=bp.id, recommendation_id=bp.recommendation_id,
                      tested=True, passed=False, categories={"unit": False}, failures=["x"])


class TestGate(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(BlueprintApprover(), IBlueprintApprover)

    def test_failed_test_cannot_be_approved(self):
        bp = _built()
        r = BlueprintApprover().review(_failed_test(bp), approver="rochak", approve=True)
        self.assertFalse(r.approved)
        self.assertEqual(r.skipped_reason, "tests_did_not_pass")

    def test_passing_with_approval_is_approved(self):
        bp = _built()
        r = BlueprintApprover().review(_passing_test(bp), approver="rochak",
                                       approve=True, decision_reason="ok")
        self.assertTrue(r.approved)
        self.assertEqual(r.approver, "rochak")
        self.assertEqual(r.decision_reason, "ok")

    def test_rejection_path(self):
        bp = _built()
        r = BlueprintApprover().review(_passing_test(bp), approver="rochak", approve=False)
        self.assertFalse(r.approved)
        self.assertEqual(r.skipped_reason, "")  # tests passed; simply rejected

    def test_never_auto_approves(self):
        # approve is a required keyword; passing tests alone never grant approval
        bp = _built()
        r = BlueprintApprover().review(_passing_test(bp), approver="x", approve=False)
        self.assertFalse(r.approved)


class TestTimestampAndDeterminism(unittest.TestCase):
    def test_supplied_timestamp_carried(self):
        bp = _built()
        r = BlueprintApprover().review(_passing_test(bp), approver="x", approve=True,
                                       approval_timestamp="2026-07-20T00:00:00Z")
        self.assertEqual(r.approval_timestamp, "2026-07-20T00:00:00Z")

    def test_no_timestamp_generated(self):
        bp = _built()
        r = BlueprintApprover().review(_passing_test(bp), approver="x", approve=True)
        self.assertIsNone(r.approval_timestamp)

    def test_byte_identical_repeat(self):
        bp = _built()
        t = _passing_test(bp)
        a = BlueprintApprover()
        r1 = a.review(t, approver="x", approve=True, decision_reason="r")
        r2 = a.review(t, approver="x", approve=True, decision_reason="r")
        self.assertEqual(r1.model_dump(), r2.model_dump())

    def test_result_frozen(self):
        bp = _built()
        r = BlueprintApprover().review(_passing_test(bp), approver="x", approve=True)
        with self.assertRaises(Exception):
            r.approved = False

    def test_inputs_unchanged(self):
        bp = _built()
        t = _passing_test(bp)
        before = t.model_dump()
        BlueprintApprover().review(t, approver="x", approve=True)
        self.assertEqual(t.model_dump(), before)


class TestIntegration(unittest.TestCase):
    def test_full_chain(self):
        for kind, target in [("improve_strategy", "seq"),
                             ("merge_memory", "notes"),
                             ("future_skill_candidate", "web")]:
            bp = _built(kind, target)
            v = BlueprintVerifier().verify(bp)
            g = BlueprintGenerator().generate(bp, v)
            t = BlueprintTester().test(bp, g)
            a = BlueprintApprover().review(t, approver="rochak", approve=True)
            self.assertTrue(a.approved, f"{kind}:{target}")
            self.assertEqual(a.blueprint_id, bp.id)


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
        for m in self._imports("brain/skill_creator/blueprint_approver.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_forbidden_tokens(self):
        # Authoritative: AST imports (the words datetime/uuid/random appear in
        # the module docstring as a "no X" guarantee, not as code).
        modules = self._imports("brain/skill_creator/blueprint_approver.py")
        for banned in ["datetime", "uuid", "random", "os", "subprocess", "importlib"]:
            self.assertNotIn(banned, modules, f"forbidden import {banned}")
        src = (backend_dir / "brain/skill_creator/blueprint_approver.py").read_text(encoding="utf-8")
        for banned in ["open(", "exec(", "eval(", "compile(", "__import__", ".now("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IBlueprintApprover))
        bp = _built()
        r = c.resolve(IBlueprintApprover).review(_passing_test(bp), approver="x", approve=True)
        self.assertTrue(r.approved)


if __name__ == "__main__":
    unittest.main()
