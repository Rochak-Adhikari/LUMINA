"""
tests/test_phase_8_step12.py — Milestone 8.12 (Failure Recovery)

Verifies the descriptive recovery advisor:

    RuntimePipelineResult → FailureRecovery → RecoveryPlan

  - completed run -> needed=False, strategy "none"
  - each failure reason maps to its deterministic strategy/retryable/rationale
  - unknown reason -> safe "none" default
  - RecoveryPlan is frozen
  - deterministic (same input -> identical plan)
  - advisor is IFailureRecovery
  - dormant DI registration + facade accessor
  - architectural boundaries (allowed imports only; no orchestration/execution)

Stdlib unittest.
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.skill_runtime.failure_recovery import FailureRecovery
from brain.skill_runtime.interfaces import IFailureRecovery
from brain.skill_runtime.models import RecoveryPlan, RuntimePipelineResult


def _result(completed=False, reason="", registry_key="fam.pkg.skill"):
    return RuntimePipelineResult(
        completed=completed, reason=reason, registry_key=registry_key
    )


class TestCompleted(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(FailureRecovery(), IFailureRecovery)

    def test_completed_needs_no_recovery(self):
        p = FailureRecovery().plan(_result(completed=True))
        self.assertFalse(p.needed)
        self.assertTrue(p.completed)
        self.assertEqual(p.strategy, "none")
        self.assertFalse(p.retryable)
        self.assertEqual(p.registry_key, "fam.pkg.skill")


class TestFailureMapping(unittest.TestCase):
    CASES = {
        "discovery_empty": ("review_required", False),
        "no_match": ("rematch_capability", False),
        "unresolved": ("review_required", False),
        "sandbox_denied": ("abort", False),
        "load_failed": ("retry_transient", True),
        "context_not_prepared": ("review_required", False),
        "execution_failed": ("retry_transient", True),
    }

    def test_each_reason_maps(self):
        rec = FailureRecovery()
        for reason, (strategy, retryable) in self.CASES.items():
            p = rec.plan(_result(reason=reason))
            self.assertTrue(p.needed, reason)
            self.assertFalse(p.completed, reason)
            self.assertEqual(p.failed_stage, reason)
            self.assertEqual(p.strategy, strategy, reason)
            self.assertEqual(p.retryable, retryable, reason)
            self.assertTrue(p.rationale, reason)

    def test_retryable_only_for_transient(self):
        rec = FailureRecovery()
        transient = {r for r, (_, rt) in self.CASES.items() if rt}
        self.assertEqual(transient, {"load_failed", "execution_failed"})
        for reason, (_, rt) in self.CASES.items():
            self.assertEqual(rec.plan(_result(reason=reason)).retryable, rt)

    def test_unknown_reason_safe_default(self):
        p = FailureRecovery().plan(_result(reason="totally_unknown"))
        self.assertTrue(p.needed)
        self.assertEqual(p.strategy, "none")
        self.assertFalse(p.retryable)
        self.assertEqual(p.failed_stage, "totally_unknown")


class TestModel(unittest.TestCase):
    def test_frozen(self):
        p = FailureRecovery().plan(_result(reason="load_failed"))
        with self.assertRaises(Exception):
            p.strategy = "hacked"

    def test_deterministic(self):
        a = FailureRecovery().plan(_result(reason="execution_failed"))
        b = FailureRecovery().plan(_result(reason="execution_failed"))
        self.assertEqual(a.model_dump(), b.model_dump())


class TestBoundaries(unittest.TestCase):
    REL = "brain/skill_runtime/failure_recovery.py"

    def _imports(self):
        src = (backend_dir / self.REL).read_text(encoding="utf-8")
        modules = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                modules.update(a.name for a in node.names)
        return modules

    def test_allowed_imports_only(self):
        allowed = (
            "brain.skill_runtime.interfaces",
            "brain.skill_runtime.models",
            "typing", "__future__",
        )
        for m in self._imports():
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_forbidden_tokens(self):
        src = (backend_dir / self.REL).read_text(encoding="utf-8")
        for banned in ["subprocess", "threading", "asyncio", "importlib",
                       "eval(", "exec(", "compile(", "open(", ".now(",
                       "requests", "sqlite", "while "]:
            self.assertNotIn(banned, src, f"forbidden token {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IFailureRecovery))
        self.assertIsInstance(c.resolve(IFailureRecovery), FailureRecovery)

    def test_facade_accessor(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        from core.runtime_facade import RuntimeFacade
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertIsInstance(RuntimeFacade(c).failure_recovery, FailureRecovery)


if __name__ == "__main__":
    unittest.main()
