"""
tests/test_phase_8_step8.py — Milestone 8.8 Verification (Execution Observer)

Purely observational: ExecutionResult -> ExecutionObservation.

Verifies:
  - frozen ExecutionObservation
  - success observation
  - failure observation
  - output type detection (dict / str / NoneType)
  - caller-supplied timestamp (never generated)
  - deterministic behavior
  - no mutation of input
  - AST boundary checks
  - dormant DI + facade accessor
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.skill_runtime.models import ExecutionObservation, ExecutionResult
from brain.skill_runtime.interfaces import IExecutionObserver
from brain.skill_runtime.execution_observer import ExecutionObserver


class TestModel(unittest.TestCase):
    def test_frozen(self):
        o = ExecutionObservation(observed=True)
        with self.assertRaises(Exception):
            o.observed = False

    def test_serializable(self):
        import json
        json.dumps(ExecutionObservation(observed=True, registry_key="k").model_dump())


class TestObserve(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(ExecutionObserver(), IExecutionObserver)

    def test_success(self):
        r = ExecutionResult(succeeded=True, output={"a": 1}, registry_key="fam.pkg")
        o = ExecutionObserver().observe(r)
        self.assertTrue(o.observed)
        self.assertTrue(o.succeeded)
        self.assertEqual(o.registry_key, "fam.pkg")
        self.assertEqual(o.output_type, "dict")
        self.assertIn("succeeded", o.summary)

    def test_failure(self):
        r = ExecutionResult(succeeded=False, registry_key="fam.pkg",
                            error="execution_failed: RuntimeError")
        o = ExecutionObserver().observe(r)
        self.assertFalse(o.succeeded)
        self.assertEqual(o.error, "execution_failed: RuntimeError")
        self.assertIn("failed", o.summary)

    def test_output_type_str(self):
        o = ExecutionObserver().observe(ExecutionResult(succeeded=True, output="hi"))
        self.assertEqual(o.output_type, "str")

    def test_output_type_none(self):
        o = ExecutionObserver().observe(ExecutionResult(succeeded=True, output=None))
        self.assertEqual(o.output_type, "NoneType")

    def test_timestamp_supplied(self):
        o = ExecutionObserver().observe(
            ExecutionResult(succeeded=True), timestamp="2026-07-20T00:00:00Z"
        )
        self.assertEqual(o.timestamp, "2026-07-20T00:00:00Z")

    def test_timestamp_none_default(self):
        o = ExecutionObserver().observe(ExecutionResult(succeeded=True))
        self.assertIsNone(o.timestamp)

    def test_deterministic(self):
        r = ExecutionResult(succeeded=True, output=[1, 2], registry_key="k")
        obs = ExecutionObserver()
        self.assertEqual(obs.observe(r).model_dump(), obs.observe(r).model_dump())

    def test_input_unchanged(self):
        r = ExecutionResult(succeeded=True, output={"x": 1}, registry_key="k")
        before = r.model_dump()
        ExecutionObserver().observe(r)
        self.assertEqual(r.model_dump(), before)


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
            "brain.skill_runtime.models",
            "brain.skill_runtime.interfaces",
            "typing", "datetime", "__future__",
        )
        for m in self._imports("brain/skill_runtime/execution_observer.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_forbidden_deps(self):
        modules = self._imports("brain/skill_runtime/execution_observer.py")
        for banned in [
            "brain.skill_creator", "brain.skill_runtime.registry_discovery",
            "brain.skill_runtime.skill_loader", "brain.skill_runtime.skill_executor",
            "brain.skill_runtime.skill_sandbox", "brain.skill_runtime.context_injector",
            "brain.workspace", "core.runtime_facade", "core.bootstrap", "server",
            "subprocess", "threading", "asyncio", "os", "importlib",
        ]:
            self.assertNotIn(banned, modules, f"observer must not import {banned}")

    def test_no_exec_tokens(self):
        src = (backend_dir / "brain/skill_runtime/execution_observer.py").read_text(encoding="utf-8")
        for banned in ["open(", "exec(", "eval(", "compile(", "__import__", ".now("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IExecutionObserver))
        self.assertTrue(c.is_registered(ExecutionObserver))
        o = c.resolve(ExecutionObserver).observe(ExecutionResult(succeeded=True))
        self.assertIsInstance(o, ExecutionObservation)

    def test_facade_accessor(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        from core.runtime_facade import RuntimeFacade
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertIsInstance(RuntimeFacade(c).execution_observer, ExecutionObserver)


if __name__ == "__main__":
    unittest.main()
