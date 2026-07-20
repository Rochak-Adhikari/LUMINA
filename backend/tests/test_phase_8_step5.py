"""
tests/test_phase_8_step5.py — Milestone 8.5 Verification (Skill Loader)

Turns an approved SandboxDecision into a loaded, validated skill instance.
Import + instantiate + interface check. NEVER executes.

Verifies:
  - frozen LoadedSkill (arbitrary instance type allowed)
  - not-approved decision -> loaded=False (not_approved)
  - no installed_location -> loaded=False
  - missing skill.py -> module_not_found
  - missing Skill class -> missing_skill_class
  - missing execute/run -> missing_entrypoint
  - valid package -> loaded=True, instance present, entrypoint recorded
  - loader does NOT call execute/run (instance untouched)
  - failure-safe (bad module never raises out)
  - no skill_creator import; dormant DI + facade accessor
"""

import ast
import tempfile
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.skill_runtime.models import (
    DiscoveredSkill,
    LoadedSkill,
    SandboxDecision,
)
from brain.skill_runtime.interfaces import ISkillLoader
from brain.skill_runtime.skill_loader import SkillLoader


_VALID_SKILL = (
    "class Skill:\n"
    "    executed = False\n"
    "    def run(self, *a, **k):\n"
    "        Skill.executed = True\n"
    "        return 'ran'\n"
)
_NO_CLASS = "x = 1\n"
_NO_ENTRY = "class Skill:\n    pass\n"
_BAD_MODULE = "raise RuntimeError('boom at import')\n"


def _decision(loc, approved=True):
    skill = DiscoveredSkill(
        blueprint_id="b", skill_family="fam", package_name="pkg",
        registry_key="fam.pkg", installed_location=loc,
        registration_status="registered",
    )
    return SandboxDecision(approved=approved, skill=skill, reason="approved")


def _write_skill(tmp, content):
    p = Path(tmp) / "skill.py"
    p.write_text(content, encoding="utf-8")
    return tmp


class TestModel(unittest.TestCase):
    def test_frozen(self):
        ls = LoadedSkill(loaded=True)
        with self.assertRaises(Exception):
            ls.loaded = False

    def test_arbitrary_instance(self):
        ls = LoadedSkill(loaded=True, instance=object())
        self.assertIsNotNone(ls.instance)


class TestLoader(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(SkillLoader(), ISkillLoader)

    def test_not_approved(self):
        r = SkillLoader().load(SandboxDecision(approved=False))
        self.assertFalse(r.loaded)
        self.assertEqual(r.error, "not_approved")

    def test_no_installed_location(self):
        r = SkillLoader().load(_decision(""))
        self.assertFalse(r.loaded)
        self.assertEqual(r.error, "no_installed_location")

    def test_module_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = SkillLoader().load(_decision(tmp))  # no skill.py
            self.assertFalse(r.loaded)
            self.assertEqual(r.error, "module_not_found")

    def test_missing_skill_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_skill(tmp, _NO_CLASS)
            r = SkillLoader().load(_decision(tmp))
            self.assertFalse(r.loaded)
            self.assertEqual(r.error, "missing_skill_class")

    def test_missing_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_skill(tmp, _NO_ENTRY)
            r = SkillLoader().load(_decision(tmp))
            self.assertFalse(r.loaded)
            self.assertEqual(r.error, "missing_entrypoint")

    def test_bad_module_failure_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_skill(tmp, _BAD_MODULE)
            r = SkillLoader().load(_decision(tmp))  # must not raise
            self.assertFalse(r.loaded)
            self.assertTrue(r.error.startswith("import_failed"))

    def test_valid_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_skill(tmp, _VALID_SKILL)
            r = SkillLoader().load(_decision(tmp))
            self.assertTrue(r.loaded, r.error)
            self.assertIsNotNone(r.instance)
            self.assertEqual(r.entrypoint, "run")
            self.assertEqual(r.skill.registry_key, "fam.pkg")

    def test_loader_does_not_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_skill(tmp, _VALID_SKILL)
            r = SkillLoader().load(_decision(tmp))
            # run() was never called by the loader
            self.assertFalse(type(r.instance).executed)

    def test_canonical_entrypoint_is_run(self):
        # Canonical runtime interface is run(); even a legacy execute() reports
        # the canonical "run" entrypoint (Phase 8.6 standardization).
        content = (
            "class Skill:\n"
            "    def execute(self, *a, **k): return 1\n"
            "    def run(self, *a, **k): return 2\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            _write_skill(tmp, content)
            r = SkillLoader().load(_decision(tmp))
            self.assertEqual(r.entrypoint, "run")

    def test_legacy_execute_only_accepted(self):
        content = "class Skill:\n    def execute(self, *a, **k): return 1\n"
        with tempfile.TemporaryDirectory() as tmp:
            _write_skill(tmp, content)
            r = SkillLoader().load(_decision(tmp))
            self.assertTrue(r.loaded)
            self.assertEqual(r.entrypoint, "run")


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

    def test_no_skill_creator_import(self):
        modules = self._imports("brain/skill_runtime/skill_loader.py")
        for banned in ["brain.skill_creator", "core.bootstrap", "server"]:
            self.assertNotIn(banned, modules, f"loader must not import {banned}")

    def test_no_execution_tokens(self):
        # loader may import a module (importlib) but must not exec/eval strings
        src = (backend_dir / "brain/skill_runtime/skill_loader.py").read_text(encoding="utf-8")
        for banned in ["subprocess", "os.system", "eval(", "exec(", "compile("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(ISkillLoader))
        self.assertTrue(c.is_registered(SkillLoader))
        r = c.resolve(SkillLoader).load(SandboxDecision(approved=False))
        self.assertIsInstance(r, LoadedSkill)

    def test_facade_accessor(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        from core.runtime_facade import RuntimeFacade
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertIsInstance(RuntimeFacade(c).skill_loader, SkillLoader)


if __name__ == "__main__":
    unittest.main()
