"""
tests/test_phase_8_step7.py — Milestone 8.7 Verification (Context Injection)

Pure transformation: LoadedSkill + caller data -> immutable ExecutionContext.

Verifies:
  - frozen models (ExecutionContext / ContextInjectionResult)
  - inject() success (context built from loaded skill + supplied data)
  - inject() failure (not loaded / no skill)
  - inputs never mutated; supplied dicts copied (not aliased)
  - no execution; deterministic
  - raw instance not read (injector works on a LoadedSkill with instance=None
    interface identity only)
  - AST boundary checks (no registry/loader/executor/skill_creator/memory imports)
  - dormant DI + facade accessor
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.skill_runtime.models import (
    ContextInjectionResult,
    DiscoveredSkill,
    ExecutionContext,
    LoadedSkill,
)
from brain.skill_runtime.interfaces import IContextInjector
from brain.skill_runtime.context_injector import ContextInjector


def _loaded(loaded=True, skill=True, instance=None):
    ds = DiscoveredSkill(blueprint_id="b", registry_key="fam.pkg",
                         registration_status="registered", installed_location="/x") if skill else None
    return LoadedSkill(loaded=loaded, skill=ds, instance=instance, entrypoint="run")


class TestModels(unittest.TestCase):
    def test_frozen(self):
        c = ExecutionContext(registry_key="k")
        with self.assertRaises(Exception):
            c.registry_key = "y"
        r = ContextInjectionResult()
        with self.assertRaises(Exception):
            r.prepared = True

    def test_serializable(self):
        import json
        r = ContextInjectionResult(prepared=True, context=ExecutionContext(registry_key="k"))
        json.dumps(r.model_dump())


class TestInject(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(ContextInjector(), IContextInjector)

    def test_success(self):
        r = ContextInjector().inject(
            _loaded(), conversation_id="c1", user_input="hi",
            available_tools=("t1", "t2"), variables={"v": 1},
        )
        self.assertTrue(r.prepared)
        self.assertEqual(r.context.registry_key, "fam.pkg")
        self.assertEqual(r.context.conversation_id, "c1")
        self.assertEqual(r.context.user_input, "hi")
        self.assertEqual(r.context.available_tools, ("t1", "t2"))
        self.assertEqual(r.context.variables, {"v": 1})

    def test_not_loaded(self):
        r = ContextInjector().inject(_loaded(loaded=False))
        self.assertFalse(r.prepared)
        self.assertEqual(r.reason, "not_loaded")

    def test_no_skill(self):
        r = ContextInjector().inject(_loaded(loaded=True, skill=False))
        self.assertFalse(r.prepared)
        self.assertEqual(r.reason, "no_skill")

    def test_inputs_not_mutated(self):
        mem = {"m": 1}
        variables = {"v": 2}
        r = ContextInjector().inject(_loaded(), memory_snapshot=mem, variables=variables)
        # mutate the returned context's source dicts? they're copies
        self.assertIsNot(r.context.memory_snapshot, mem)
        self.assertIsNot(r.context.variables, variables)
        # originals unchanged
        self.assertEqual(mem, {"m": 1})
        self.assertEqual(variables, {"v": 2})

    def test_defaults_empty(self):
        r = ContextInjector().inject(_loaded())
        self.assertEqual(r.context.memory_snapshot, {})
        self.assertEqual(r.context.available_tools, ())

    def test_deterministic(self):
        inj = ContextInjector()
        a = inj.inject(_loaded(), user_input="x")
        b = inj.inject(_loaded(), user_input="x")
        self.assertEqual(a.model_dump(), b.model_dump())

    def test_does_not_read_instance(self):
        # instance=None but loaded True + skill present -> still prepares context
        r = ContextInjector().inject(_loaded(instance=None))
        self.assertTrue(r.prepared)


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
        for m in self._imports("brain/skill_runtime/context_injector.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_forbidden_deps(self):
        modules = self._imports("brain/skill_runtime/context_injector.py")
        for banned in ["brain.skill_creator", "brain.skill_runtime.registry_discovery",
                       "brain.skill_runtime.skill_loader", "brain.skill_runtime.skill_executor",
                       "brain.skill_runtime.skill_sandbox", "brain.workspace",
                       "core.bootstrap", "server"]:
            self.assertNotIn(banned, modules, f"injector must not import {banned}")

    def test_no_io_tokens(self):
        modules = self._imports("brain/skill_runtime/context_injector.py")
        for banned in ["subprocess", "os", "socket", "requests", "importlib"]:
            self.assertNotIn(banned, modules, f"forbidden import {banned}")
        src = (backend_dir / "brain/skill_runtime/context_injector.py").read_text(encoding="utf-8")
        for banned in ["open(", "exec(", "eval(", "compile(", "__import__", ".now("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IContextInjector))
        self.assertTrue(c.is_registered(ContextInjector))
        r = c.resolve(ContextInjector).inject(_loaded())
        self.assertIsInstance(r, ContextInjectionResult)

    def test_facade_accessor(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        from core.runtime_facade import RuntimeFacade
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertIsInstance(RuntimeFacade(c).context_injector, ContextInjector)


if __name__ == "__main__":
    unittest.main()
