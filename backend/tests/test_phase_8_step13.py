"""
tests/test_phase_8_step13.py — Milestone 8.13 (Runtime Validation)

Verifies the read-only integrity checker:

    RuntimePipelineResult → RuntimeValidator → ValidationReport

  - completed run (all stages populated, empty reason) -> valid
  - each failure reason with the correct populated prefix -> valid
  - execution_failed (full tail populated) -> valid
  - noncontiguous stages -> violation
  - completed with reason / completed but incomplete -> violations
  - failed without reason / unknown reason / reason-stage mismatch -> violations
  - ValidationReport frozen
  - deterministic (same input -> identical report)
  - validator is IRuntimeValidator
  - dormant DI registration + facade accessor
  - architectural boundaries (allowed imports only; no repair/execution)

Stdlib unittest.
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.skill_runtime.runtime_validation import RuntimeValidator
from brain.skill_runtime.interfaces import IRuntimeValidator
from brain.skill_runtime.models import (
    RuntimePipelineResult,
    ValidationReport,
    RegistrySearchResult,
    CapabilityMatchResult,
    DependencyResolution,
    SandboxDecision,
    LoadedSkill,
    ContextInjectionResult,
    ExecutionResult,
    ExecutionObservation,
    ExecutionRecord,
    PersistenceResult,
)

# Non-None sentinels for each stage field, in pipeline order.
_STAGE_VALUES = {
    "discovery": RegistrySearchResult(),
    "match": CapabilityMatchResult(),
    "resolution": DependencyResolution(),
    "sandbox": SandboxDecision(),
    "loaded": LoadedSkill(),
    "context": ContextInjectionResult(),
    "execution": ExecutionResult(),
    "observation": ExecutionObservation(),
    "record": ExecutionRecord(),
    "persistence": PersistenceResult(),
}
_ORDER = list(_STAGE_VALUES)


def _result(prefix, *, completed=False, reason="", registry_key=""):
    """Build a result with the first ``prefix`` stages populated."""
    kw = {name: _STAGE_VALUES[name] for name in _ORDER[:prefix]}
    return RuntimePipelineResult(
        completed=completed, reason=reason, registry_key=registry_key, **kw
    )


class TestValid(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(RuntimeValidator(), IRuntimeValidator)

    def test_completed_all_stages_valid(self):
        r = _result(10, completed=True, reason="")
        rep = RuntimeValidator().validate(r)
        self.assertTrue(rep.valid, rep.violations)
        self.assertTrue(rep.completed)
        self.assertEqual(rep.last_stage, "persistence")
        self.assertEqual(rep.violations, ())
        self.assertEqual(rep.checked, 3)

    def test_each_failure_prefix_valid(self):
        cases = {
            "discovery_empty": 1,
            "no_match": 2,
            "unresolved": 3,
            "sandbox_denied": 4,
            "load_failed": 5,
            "context_not_prepared": 6,
            "execution_failed": 10,  # observer→recorder→persistence tail runs
        }
        v = RuntimeValidator()
        for reason, prefix in cases.items():
            rep = v.validate(_result(prefix, reason=reason))
            self.assertTrue(rep.valid, f"{reason}: {rep.violations}")
            self.assertFalse(rep.completed, reason)


class TestViolations(unittest.TestCase):
    def setUp(self):
        self.v = RuntimeValidator()

    def test_noncontiguous(self):
        # discovery + resolution populated, match missing -> gap.
        r = RuntimePipelineResult(
            discovery=RegistrySearchResult(),
            resolution=DependencyResolution(),
            reason="unresolved",
        )
        rep = self.v.validate(r)
        self.assertFalse(rep.valid)
        self.assertIn("noncontiguous_stages", rep.violations)

    def test_completed_with_reason(self):
        rep = self.v.validate(_result(10, completed=True, reason="no_match"))
        self.assertFalse(rep.valid)
        self.assertIn("completed_with_reason", rep.violations)

    def test_completed_but_incomplete(self):
        rep = self.v.validate(_result(5, completed=True, reason=""))
        self.assertFalse(rep.valid)
        self.assertIn("completed_but_incomplete", rep.violations)

    def test_failed_without_reason(self):
        rep = self.v.validate(_result(2, completed=False, reason=""))
        self.assertFalse(rep.valid)
        self.assertIn("failed_without_reason", rep.violations)

    def test_unknown_reason(self):
        rep = self.v.validate(_result(2, reason="bogus"))
        self.assertFalse(rep.valid)
        self.assertIn("unknown_reason", rep.violations)

    def test_reason_stage_mismatch(self):
        # reason says no_match (expects last=match) but prefix reaches sandbox.
        rep = self.v.validate(_result(4, reason="no_match"))
        self.assertFalse(rep.valid)
        self.assertIn("reason_stage_mismatch", rep.violations)


class TestModel(unittest.TestCase):
    def test_frozen(self):
        rep = RuntimeValidator().validate(_result(10, completed=True))
        with self.assertRaises(Exception):
            rep.valid = False

    def test_deterministic(self):
        a = RuntimeValidator().validate(_result(5, reason="load_failed"))
        b = RuntimeValidator().validate(_result(5, reason="load_failed"))
        self.assertEqual(a.model_dump(), b.model_dump())


class TestBoundaries(unittest.TestCase):
    REL = "brain/skill_runtime/runtime_validation.py"

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
                       "requests", "sqlite"]:
            self.assertNotIn(banned, src, f"forbidden token {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IRuntimeValidator))
        self.assertIsInstance(c.resolve(IRuntimeValidator), RuntimeValidator)

    def test_facade_accessor(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        from core.runtime_facade import RuntimeFacade
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertIsInstance(RuntimeFacade(c).runtime_validator, RuntimeValidator)


if __name__ == "__main__":
    unittest.main()
