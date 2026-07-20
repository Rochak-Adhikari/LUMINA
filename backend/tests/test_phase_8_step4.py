"""
tests/test_phase_8_step4.py — Milestone 8.4 Verification (Skill Sandbox)

First runtime execution-safety layer. SkillSandbox: DependencyResolution +
SandboxPolicy -> SandboxDecision (allow/deny). Gatekeeper only — no load, no exec.

Verifies:
  - frozen models (SandboxPolicy / SandboxDecision)
  - unresolved resolution denied (require_resolved)
  - resolved + permissions within allowlist -> approved
  - permission outside allowlist -> denied (permission_denied violation)
  - unsatisfied requirement -> denied
  - no skill present -> denied
  - require_resolved=False bypasses the resolved gate (still needs a skill)
  - deterministic / repeatable
  - depends only on 8.3 output; no registry/skill_creator imports; no I/O
  - dormant DI + RuntimeFacade accessor
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.skill_runtime.models import (
    DependencyRequirement,
    DependencyResolution,
    DiscoveredSkill,
    SandboxDecision,
    SandboxPolicy,
)
from brain.skill_runtime.interfaces import ISkillSandbox
from brain.skill_runtime.skill_sandbox import SkillSandbox


def _skill():
    return DiscoveredSkill(blueprint_id="b", skill_family="fam", package_name="pkg",
                           registry_key="k", installed_location="/x",
                           registration_status="registered")


def _resolution(resolved=True, skill=True, reqs=None):
    return DependencyResolution(
        resolved=resolved,
        skill=_skill() if skill else None,
        requirements=reqs or [],
        reason="resolved" if resolved else "x",
    )


def _perm(value, satisfied=True):
    return DependencyRequirement(kind="permission", value=value, satisfied=satisfied)


class TestModels(unittest.TestCase):
    def test_frozen(self):
        p = SandboxPolicy()
        with self.assertRaises(Exception):
            p.require_resolved = False
        d = SandboxDecision()
        with self.assertRaises(Exception):
            d.approved = True

    def test_serializable(self):
        import json
        json.dumps(SandboxDecision(approved=True, skill=_skill()).model_dump())


class TestSandbox(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(SkillSandbox(), ISkillSandbox)

    def test_unresolved_denied(self):
        d = SkillSandbox().evaluate(_resolution(resolved=False, skill=False), SandboxPolicy())
        self.assertFalse(d.approved)
        self.assertIn("not_resolved", d.violations)

    def test_no_skill_denied(self):
        d = SkillSandbox().evaluate(_resolution(resolved=True, skill=False), SandboxPolicy())
        self.assertFalse(d.approved)
        self.assertIn("no_skill", d.violations)

    def test_approved_clean(self):
        d = SkillSandbox().evaluate(_resolution(), SandboxPolicy())
        self.assertTrue(d.approved)
        self.assertEqual(d.violations, ())
        self.assertIsNotNone(d.skill)

    def test_permission_within_allowlist(self):
        res = _resolution(reqs=[_perm("filesystem.read")])
        pol = SandboxPolicy(allowed_permissions=("filesystem.read", "network.http"))
        d = SkillSandbox().evaluate(res, pol)
        self.assertTrue(d.approved)

    def test_permission_outside_allowlist_denied(self):
        res = _resolution(reqs=[_perm("filesystem.write")])
        pol = SandboxPolicy(allowed_permissions=("filesystem.read",))
        d = SkillSandbox().evaluate(res, pol)
        self.assertFalse(d.approved)
        self.assertIn("permission_denied:filesystem.write", d.violations)

    def test_unsatisfied_requirement_denied(self):
        res = _resolution(reqs=[DependencyRequirement(kind="install", value="installed_location", satisfied=False)])
        d = SkillSandbox().evaluate(res, SandboxPolicy())
        self.assertFalse(d.approved)
        self.assertIn("unsatisfied:installed_location", d.violations)

    def test_require_resolved_false_bypasses_gate(self):
        # not resolved but require_resolved False + skill present -> evaluated
        res = _resolution(resolved=False, skill=True)
        pol = SandboxPolicy(require_resolved=False)
        d = SkillSandbox().evaluate(res, pol)
        self.assertTrue(d.approved)

    def test_repeatable(self):
        res = _resolution(reqs=[_perm("filesystem.read")])
        pol = SandboxPolicy(allowed_permissions=("filesystem.read",))
        s = SkillSandbox()
        self.assertEqual(s.evaluate(res, pol).model_dump(), s.evaluate(res, pol).model_dump())


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
            "typing", "abc", "__future__",
        )
        for m in self._imports("brain/skill_runtime/skill_sandbox.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_registry_skill_creator(self):
        modules = self._imports("brain/skill_runtime/skill_sandbox.py")
        for banned in ["brain.skill_creator", "brain.skill_runtime.registry_discovery",
                       "brain.skill_runtime.dependency_resolver", "core.bootstrap", "server"]:
            self.assertNotIn(banned, modules, f"sandbox must not import {banned}")

    def test_no_exec_or_load_tokens(self):
        modules = self._imports("brain/skill_runtime/skill_sandbox.py")
        for banned in ["subprocess", "os", "importlib", "socket", "requests"]:
            self.assertNotIn(banned, modules, f"forbidden import {banned}")
        src = (backend_dir / "brain/skill_runtime/skill_sandbox.py").read_text(encoding="utf-8")
        for banned in ["open(", "exec(", "eval(", "compile(", "__import__", ".now("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(ISkillSandbox))
        self.assertTrue(c.is_registered(SkillSandbox))
        d = c.resolve(SkillSandbox).evaluate(_resolution(), SandboxPolicy())
        self.assertIsInstance(d, SandboxDecision)

    def test_facade_accessor(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        from core.runtime_facade import RuntimeFacade
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertIsInstance(RuntimeFacade(c).skill_sandbox, SkillSandbox)


if __name__ == "__main__":
    unittest.main()
