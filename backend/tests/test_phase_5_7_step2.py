"""
tests/test_phase_5_7_step2.py — Phase 5.7.2: ReflectionEngine

Pure deterministic read-only evaluator. Reuses the existing Reflection model.
No DI, no BrainCore, no integration.
"""

import unittest
from unittest.mock import MagicMock
from pathlib import Path
from types import SimpleNamespace
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

sys.modules.setdefault('google', MagicMock())
sys.modules.setdefault('google.genai', MagicMock())
sys.modules.setdefault('google.genai.types', MagicMock())

from brain.reflection.engine import ReflectionEngine
from brain.reflection.interfaces import IReflectionEngine
from brain.core.models import BrainRequest, Plan, Task, Reflection
from brain.skills.models import SkillResult


def _req():
    return BrainRequest(text="x", request_id="req-1")


def _plan(pid="plan-1", conf=1.0, n=1):
    return Plan(plan_id=pid, tasks=[Task(intent="t", skill_id=f"s{i}") for i in range(n)],
                confidence=conf)


def _ok(sid, latency=None):
    return SkillResult(skill_id=sid, ok=True, latency_ms=latency)


def _fail(sid, err="boom", latency=None):
    return SkillResult(skill_id=sid, ok=False, error=err, latency_ms=latency)


class TestContract(unittest.TestCase):
    def test_implements_interface(self):
        self.assertIsInstance(ReflectionEngine(), IReflectionEngine)

    def test_returns_reflection(self):
        r = ReflectionEngine().reflect(_req(), _plan(), [_ok("s0")])
        self.assertIsInstance(r, Reflection)

    def test_reuses_existing_model(self):
        # Same Reflection class as brain.core.models (not a redefinition).
        from brain.core.models import Reflection as CoreReflection
        r = ReflectionEngine().reflect(_req(), _plan(), [_ok("s0")])
        self.assertIs(type(r), CoreReflection)


class TestComputation(unittest.TestCase):
    def setUp(self):
        self.e = ReflectionEngine()

    def test_request_and_plan_id(self):
        r = self.e.reflect(_req(), _plan(pid="P"), [_ok("s0")])
        self.assertEqual(r.request_id, "req-1")
        self.assertEqual(r.plan_id, "P")

    def test_success_all_ok(self):
        r = self.e.reflect(_req(), _plan(n=2), [_ok("a"), _ok("b")])
        self.assertTrue(r.success)
        self.assertEqual(r.failures, [])

    def test_failure_any_fail(self):
        r = self.e.reflect(_req(), _plan(n=2), [_ok("a"), _fail("b", "nope")])
        self.assertFalse(r.success)
        self.assertEqual(len(r.failures), 1)
        self.assertEqual(r.failures[0]["skill_id"], "b")
        self.assertEqual(r.failures[0]["error"], "nope")

    def test_no_results_not_success(self):
        r = self.e.reflect(_req(), _plan(), [])
        self.assertFalse(r.success)
        self.assertEqual(r.notes, "No skills executed.")

    def test_skills_used_extraction_order(self):
        r = self.e.reflect(_req(), _plan(n=3), [_ok("a"), _fail("b"), _ok("c")])
        self.assertEqual(r.skills_used, ["a", "b", "c"])

    def test_skills_used_skips_missing_id(self):
        r = self.e.reflect(_req(), _plan(), [SimpleNamespace(ok=True, skill_id="")])
        self.assertEqual(r.skills_used, [])

    def test_latency_sum_or_none(self):
        self.assertEqual(
            self.e.reflect(_req(), _plan(n=2), [_ok("a", 10.0), _ok("b", 5.0)]).latency_ms,
            15.0)
        self.assertIsNone(self.e.reflect(_req(), _plan(), [_ok("a")]).latency_ms)

    def test_confidence_full_success(self):
        r = self.e.reflect(_req(), _plan(conf=0.8, n=2), [_ok("a"), _ok("b")])
        self.assertAlmostEqual(r.confidence, 0.8)

    def test_confidence_partial(self):
        r = self.e.reflect(_req(), _plan(conf=1.0, n=2), [_ok("a"), _fail("b")])
        self.assertAlmostEqual(r.confidence, 0.5)  # 1.0 * (1/2)

    def test_confidence_no_results_zero(self):
        self.assertEqual(self.e.reflect(_req(), _plan(), []).confidence, 0.0)

    def test_corrections_default_empty(self):
        self.assertEqual(self.e.reflect(_req(), _plan(), [_ok("a")]).corrections, [])

    def test_notes_variants(self):
        self.assertEqual(self.e.reflect(_req(), _plan(n=2),
                         [_ok("a"), _ok("b")]).notes, "All 2 task(s) succeeded.")
        self.assertEqual(self.e.reflect(_req(), _plan(n=2),
                         [_ok("a"), _fail("b")]).notes, "1 of 2 task(s) failed.")

    def test_no_plan_safe(self):
        r = self.e.reflect(_req(), None, [_ok("a")])
        self.assertIsNone(r.plan_id)
        self.assertTrue(r.success)


class TestDeterminismAndPurity(unittest.TestCase):
    def test_deterministic(self):
        e = ReflectionEngine()
        results = [_ok("a", 3.0), _fail("b")]
        a = e.reflect(_req(), _plan(n=2), results).model_dump()
        b = e.reflect(_req(), _plan(n=2), results).model_dump()
        self.assertEqual(a, b)

    def test_does_not_mutate_inputs(self):
        results = [_ok("a"), _fail("b")]
        before = [r.model_dump() for r in results]
        ReflectionEngine().reflect(_req(), _plan(n=2), results)
        self.assertEqual([r.model_dump() for r in results], before)

    def test_engine_owns_no_state(self):
        # Two calls with different inputs don't bleed state.
        e = ReflectionEngine()
        r1 = e.reflect(_req(), _plan(), [_ok("a")])
        r2 = e.reflect(_req(), _plan(), [_fail("b")])
        self.assertTrue(r1.success)
        self.assertFalse(r2.success)


class TestNoForbiddenImports(unittest.TestCase):
    def test_engine_imports_whitelist(self):
        import ast
        allowed_roots = {"__future__", "typing", "abc", "brain"}
        for fname in ("engine.py", "interfaces.py"):
            src = (backend_dir / "brain" / "reflection" / fname).read_text(encoding="utf-8")
            for n in ast.walk(ast.parse(src)):
                mod = None
                if isinstance(n, ast.ImportFrom) and n.module:
                    mod = n.module
                elif isinstance(n, ast.Import):
                    mod = n.names[0].name
                if not mod:
                    continue
                root = mod.split(".")[0]
                self.assertIn(root, allowed_roots, f"{fname}: unexpected import {mod}")
                # brain imports limited to brain.core.models / brain.reflection.*
                if root == "brain":
                    self.assertTrue(
                        mod.startswith("brain.core.models") or mod.startswith("brain.reflection"),
                        f"{fname}: forbidden brain import {mod}")
                # explicit forbidden substrings
                for bad in ("planning", "skills", "workspace", "project_manager",
                            "brain.core.brain_core", "server", "lumina", "memory_engine"):
                    self.assertNotIn(bad, mod, f"{fname}: forbidden import {mod}")


if __name__ == '__main__':
    unittest.main()
