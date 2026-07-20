"""
tests/test_phase_8_step6.py — Milestone 8.6 Verification (Skill Executor)

Runs a loaded skill exactly once via canonical run(context). Never retries,
recovers, or chains. Converts failures into structured ExecutionResult.

Verifies:
  - frozen ExecutionResult (arbitrary output allowed)
  - successful execution (output captured; run called once)
  - execution failure (skill raises) -> succeeded=False, structured error
  - unloaded skill -> not_loaded
  - loaded=True but no instance -> not_loaded
  - instance without run/execute -> no_entrypoint
  - legacy execute() shim runs
  - deterministic / no multiple executions
  - depends only on 8.5 output; no registry/skill_creator imports
  - dormant DI + facade accessor
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.skill_runtime.models import (
    DiscoveredSkill,
    ExecutionResult,
    LoadedSkill,
)
from brain.skill_runtime.interfaces import ISkillExecutor
from brain.skill_runtime.skill_executor import SkillExecutor


class _RunSkill:
    def __init__(self):
        self.calls = 0
    def run(self, context=None):
        self.calls += 1
        return {"ctx": context, "ok": True}


class _BoomSkill:
    def run(self, context=None):
        raise RuntimeError("kaboom")


class _ExecuteOnly:
    def execute(self, context=None):
        return "legacy-ran"


class _NoEntry:
    pass


def _loaded(instance, key="fam.pkg"):
    skill = DiscoveredSkill(blueprint_id="b", registry_key=key,
                            registration_status="registered", installed_location="/x")
    return LoadedSkill(loaded=True, skill=skill, instance=instance, entrypoint="run")


class TestModel(unittest.TestCase):
    def test_frozen(self):
        r = ExecutionResult(succeeded=True)
        with self.assertRaises(Exception):
            r.succeeded = False

    def test_arbitrary_output(self):
        r = ExecutionResult(succeeded=True, output=object())
        self.assertIsNotNone(r.output)


class TestExecutor(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(SkillExecutor(), ISkillExecutor)

    def test_success(self):
        inst = _RunSkill()
        r = SkillExecutor().execute(_loaded(inst), context={"a": 1})
        self.assertTrue(r.succeeded)
        self.assertEqual(r.output["ctx"], {"a": 1})
        self.assertEqual(r.registry_key, "fam.pkg")
        self.assertEqual(inst.calls, 1)  # exactly once

    def test_failure_captured(self):
        r = SkillExecutor().execute(_loaded(_BoomSkill()))
        self.assertFalse(r.succeeded)
        self.assertTrue(r.error.startswith("execution_failed"))

    def test_unloaded(self):
        r = SkillExecutor().execute(LoadedSkill(loaded=False))
        self.assertFalse(r.succeeded)
        self.assertEqual(r.error, "not_loaded")

    def test_loaded_no_instance(self):
        r = SkillExecutor().execute(LoadedSkill(loaded=True, instance=None))
        self.assertFalse(r.succeeded)
        self.assertEqual(r.error, "not_loaded")

    def test_no_entrypoint(self):
        r = SkillExecutor().execute(_loaded(_NoEntry()))
        self.assertFalse(r.succeeded)
        self.assertEqual(r.error, "no_entrypoint")

    def test_legacy_execute_shim(self):
        r = SkillExecutor().execute(_loaded(_ExecuteOnly()))
        self.assertTrue(r.succeeded)
        self.assertEqual(r.output, "legacy-ran")

    def test_no_multiple_executions(self):
        inst = _RunSkill()
        ex = SkillExecutor()
        ex.execute(_loaded(inst))
        ex.execute(_loaded(inst))
        self.assertEqual(inst.calls, 2)  # one per execute call, never doubled

    def test_deterministic_result_shape(self):
        r1 = SkillExecutor().execute(_loaded(_RunSkill()))
        r2 = SkillExecutor().execute(_loaded(_RunSkill()))
        self.assertEqual(r1.succeeded, r2.succeeded)
        self.assertEqual(r1.registry_key, r2.registry_key)


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
            "__future__",
        )
        for m in self._imports("brain/skill_runtime/skill_executor.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_registry_skill_creator(self):
        modules = self._imports("brain/skill_runtime/skill_executor.py")
        for banned in ["brain.skill_creator", "brain.skill_runtime.registry_discovery",
                       "brain.skill_runtime.skill_loader", "core.bootstrap", "server"]:
            self.assertNotIn(banned, modules, f"executor must not import {banned}")

    def test_no_orchestration_tokens(self):
        src = (backend_dir / "brain/skill_runtime/skill_executor.py").read_text(encoding="utf-8")
        for banned in ["subprocess", "importlib", "asyncio", "threading",
                       "retry", "while ", "eval(", "compile("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(ISkillExecutor))
        self.assertTrue(c.is_registered(SkillExecutor))
        r = c.resolve(SkillExecutor).execute(LoadedSkill(loaded=False))
        self.assertIsInstance(r, ExecutionResult)

    def test_facade_accessor(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        from core.runtime_facade import RuntimeFacade
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertIsInstance(RuntimeFacade(c).skill_executor, SkillExecutor)


if __name__ == "__main__":
    unittest.main()
