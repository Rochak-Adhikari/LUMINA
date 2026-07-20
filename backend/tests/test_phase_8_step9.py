"""
tests/test_phase_8_step9.py — Milestone 8.9 Verification (Execution Recorder)

Pure transformation: ExecutionObservation -> ExecutionRecord. No persistence.

Verifies:
  - frozen ExecutionRecord
  - successful recording
  - failed (not observed) -> recorded=False, reason=not_observed
  - metadata copied + not aliased; inputs not mutated
  - timestamp caller-supplied / None
  - deterministic
  - AST boundary checks
  - dormant DI + facade accessor
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.skill_runtime.models import ExecutionObservation, ExecutionRecord
from brain.skill_runtime.interfaces import IExecutionRecorder
from brain.skill_runtime.execution_recorder import ExecutionRecorder


def _obs(observed=True, succeeded=True):
    return ExecutionObservation(
        observed=observed, registry_key="fam.pkg", succeeded=succeeded,
        error="" if succeeded else "boom", output_type="dict",
        summary="skill 'fam.pkg' succeeded (output: dict)",
    )


class TestModel(unittest.TestCase):
    def test_frozen(self):
        r = ExecutionRecord(recorded=True)
        with self.assertRaises(Exception):
            r.recorded = False

    def test_serializable(self):
        import json
        json.dumps(ExecutionRecord(recorded=True, registry_key="k").model_dump())


class TestRecord(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(ExecutionRecorder(), IExecutionRecorder)

    def test_success(self):
        r = ExecutionRecorder().record(_obs(), conversation_id="c1")
        self.assertTrue(r.recorded)
        self.assertEqual(r.registry_key, "fam.pkg")
        self.assertEqual(r.conversation_id, "c1")
        self.assertTrue(r.succeeded)
        self.assertEqual(r.output_type, "dict")
        self.assertEqual(r.reason, "recorded")
        self.assertIn("succeeded", r.summary)

    def test_failed_observation_not_recorded(self):
        r = ExecutionRecorder().record(_obs(observed=False))
        self.assertFalse(r.recorded)
        self.assertEqual(r.reason, "not_observed")

    def test_failure_carried(self):
        r = ExecutionRecorder().record(_obs(succeeded=False))
        self.assertFalse(r.succeeded)
        self.assertEqual(r.error, "boom")

    def test_metadata_copied_not_aliased(self):
        meta = {"k": {"nested": 1}}
        r = ExecutionRecorder().record(_obs(), metadata=meta)
        self.assertIsNot(r.metadata, meta)
        self.assertIsNot(r.metadata["k"], meta["k"])  # deep copy
        self.assertEqual(r.metadata, {"k": {"nested": 1}})

    def test_inputs_not_mutated(self):
        obs = _obs()
        meta = {"a": 1}
        before_obs = obs.model_dump()
        ExecutionRecorder().record(obs, metadata=meta)
        self.assertEqual(obs.model_dump(), before_obs)
        self.assertEqual(meta, {"a": 1})

    def test_timestamp_supplied(self):
        r = ExecutionRecorder().record(_obs(), timestamp="2026-07-20T00:00:00Z")
        self.assertEqual(r.timestamp, "2026-07-20T00:00:00Z")

    def test_timestamp_none(self):
        self.assertIsNone(ExecutionRecorder().record(_obs()).timestamp)

    def test_deterministic(self):
        rec = ExecutionRecorder()
        a = rec.record(_obs(), conversation_id="c", metadata={"m": 1})
        b = rec.record(_obs(), conversation_id="c", metadata={"m": 1})
        self.assertEqual(a.model_dump(), b.model_dump())

    def test_defaults(self):
        r = ExecutionRecorder().record(_obs())
        self.assertEqual(r.metadata, {})
        self.assertEqual(r.conversation_id, "")


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
            "typing", "copy", "__future__",
        )
        for m in self._imports("brain/skill_runtime/execution_recorder.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_forbidden_deps(self):
        modules = self._imports("brain/skill_runtime/execution_recorder.py")
        for banned in [
            "brain.skill_creator", "brain.skill_runtime.registry_discovery",
            "brain.skill_runtime.skill_executor", "brain.skill_runtime.execution_observer",
            "brain.workspace", "core.runtime_facade", "core.bootstrap", "server",
            "os", "pathlib", "subprocess", "threading", "asyncio", "importlib",
            "logging", "sqlite3", "requests", "socket",
        ]:
            self.assertNotIn(banned, modules, f"recorder must not import {banned}")

    def test_no_io_or_clock_tokens(self):
        src = (backend_dir / "brain/skill_runtime/execution_recorder.py").read_text(encoding="utf-8")
        for banned in ["open(", "exec(", "eval(", "compile(", "__import__", ".now(", ".write("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IExecutionRecorder))
        self.assertTrue(c.is_registered(ExecutionRecorder))
        r = c.resolve(ExecutionRecorder).record(_obs())
        self.assertIsInstance(r, ExecutionRecord)

    def test_facade_accessor(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        from core.runtime_facade import RuntimeFacade
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertIsInstance(RuntimeFacade(c).execution_recorder, ExecutionRecorder)


if __name__ == "__main__":
    unittest.main()
