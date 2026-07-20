"""
tests/test_phase_8_step10.py — Milestone 8.10 Verification (Execution Persistence)

Prepare step (NOT storage): ExecutionRecord -> PersistenceResult.

Verifies:
  - frozen PersistenceResult
  - prepare success (recorded record -> persistable)
  - prepare failure (not recorded -> not_persistable, reason)
  - storage_key passthrough (caller-supplied)
  - deterministic output; input unchanged
  - AST boundary checks (no IO/serialization/service imports)
  - dormant DI + facade accessor
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.skill_runtime.models import ExecutionRecord, PersistenceResult
from brain.skill_runtime.interfaces import IExecutionPersistence
from brain.skill_runtime.execution_persistence import ExecutionPersistence


def _record(recorded=True):
    return ExecutionRecord(
        recorded=recorded, registry_key="fam.pkg", conversation_id="c1",
        summary="ok", succeeded=True, output_type="dict",
    )


class TestModel(unittest.TestCase):
    def test_frozen(self):
        r = PersistenceResult(persistable=True)
        with self.assertRaises(Exception):
            r.persistable = False

    def test_serializable(self):
        import json
        json.dumps(PersistenceResult(persistable=True, record=_record(),
                                     storage_key="k").model_dump())


class TestPrepare(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(ExecutionPersistence(), IExecutionPersistence)

    def test_success(self):
        r = ExecutionPersistence().prepare(_record(), storage_key="runs/1")
        self.assertTrue(r.persistable)
        self.assertIsNotNone(r.record)
        self.assertEqual(r.record.registry_key, "fam.pkg")
        self.assertEqual(r.storage_key, "runs/1")
        self.assertEqual(r.reason, "")

    def test_not_recorded(self):
        r = ExecutionPersistence().prepare(_record(recorded=False))
        self.assertFalse(r.persistable)
        self.assertIsNone(r.record)
        self.assertEqual(r.reason, "not_recorded")

    def test_storage_key_passthrough(self):
        r = ExecutionPersistence().prepare(_record(), storage_key="abc-123")
        self.assertEqual(r.storage_key, "abc-123")

    def test_storage_key_default_empty(self):
        r = ExecutionPersistence().prepare(_record())
        self.assertEqual(r.storage_key, "")

    def test_deterministic(self):
        p = ExecutionPersistence()
        a = p.prepare(_record(), storage_key="k")
        b = p.prepare(_record(), storage_key="k")
        self.assertEqual(a.model_dump(), b.model_dump())

    def test_input_unchanged(self):
        rec = _record()
        before = rec.model_dump()
        ExecutionPersistence().prepare(rec, storage_key="k")
        self.assertEqual(rec.model_dump(), before)


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
            "typing", "__future__",
        )
        for m in self._imports("brain/skill_runtime/execution_persistence.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_forbidden_deps(self):
        modules = self._imports("brain/skill_runtime/execution_persistence.py")
        for banned in [
            "brain.skill_creator", "brain.workspace",
            "brain.skill_runtime.execution_recorder",
            "brain.skill_runtime.execution_observer", "core.runtime_facade",
            "core.bootstrap", "server",
            "os", "pathlib", "sqlite3", "subprocess", "threading", "asyncio",
            "logging", "json", "pickle", "importlib", "requests", "socket",
        ]:
            self.assertNotIn(banned, modules, f"persistence must not import {banned}")

    def test_no_io_serialize_tokens(self):
        src = (backend_dir / "brain/skill_runtime/execution_persistence.py").read_text(encoding="utf-8")
        for banned in ["open(", ".write(", "exec(", "eval(", "compile(",
                       "__import__", ".now(", "dumps(", "dump("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IExecutionPersistence))
        self.assertTrue(c.is_registered(ExecutionPersistence))
        r = c.resolve(ExecutionPersistence).prepare(_record())
        self.assertIsInstance(r, PersistenceResult)

    def test_facade_accessor(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        from core.runtime_facade import RuntimeFacade
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertIsInstance(RuntimeFacade(c).execution_persistence, ExecutionPersistence)


if __name__ == "__main__":
    unittest.main()
