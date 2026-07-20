"""
tests/test_phase_8_step3.py — Milestone 8.3 Verification (Dependency Resolution)

Gate between matching and loading. DependencyResolver: CapabilityMatchResult +
grants -> DependencyResolution.

Verifies:
  - frozen models (DependencyRequirement / DependencyResolution)
  - empty matches -> not resolved (no_candidates)
  - registered + installed skill -> resolved, top-ranked chosen
  - unregistered / no-install -> unsatisfied
  - capability restriction gating
  - runtime_version recorded satisfied (deferred to 8.9)
  - permission grants recorded (enforcement deferred to 8.4)
  - deterministic (first satisfied in match order wins); repeatable
  - depends only on 8.2 output; no registry/skill_creator imports; no I/O
  - dormant DI + RuntimeFacade accessor
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.skill_runtime.models import (
    CapabilityMatch,
    CapabilityMatchResult,
    DependencyRequirement,
    DependencyResolution,
    DiscoveredSkill,
)
from brain.skill_runtime.interfaces import IDependencyResolver
from brain.skill_runtime.dependency_resolver import DependencyResolver


def _skill(family="fam", package="pkg", key=None, status="registered", loc="/x"):
    return DiscoveredSkill(
        blueprint_id="b", skill_family=family, package_name=package,
        semantic_fingerprint="fp", registry_key=key or f"{family}.{package}",
        installed_location=loc, registration_status=status,
    )


def _matches(*skills, scores=None):
    scores = scores or [100] * len(skills)
    ms = [CapabilityMatch(skill=s, score=sc, reason="x") for s, sc in zip(skills, scores)]
    return CapabilityMatchResult(matches=ms, match_count=len(ms), capability="cap")


class TestModels(unittest.TestCase):
    def test_frozen(self):
        r = DependencyRequirement(kind="permission")
        with self.assertRaises(Exception):
            r.satisfied = True
        res = DependencyResolution()
        with self.assertRaises(Exception):
            res.resolved = True

    def test_serializable(self):
        import json
        res = DependencyResolution(
            resolved=True, skill=_skill(),
            requirements=[DependencyRequirement(kind="install", value="x", satisfied=True)],
        )
        json.dumps(res.model_dump())


class TestResolve(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(DependencyResolver(), IDependencyResolver)

    def test_no_candidates(self):
        r = DependencyResolver().resolve(CapabilityMatchResult())
        self.assertFalse(r.resolved)
        self.assertIsNone(r.skill)
        self.assertEqual(r.reason, "no_candidates")

    def test_registered_installed_resolves(self):
        r = DependencyResolver().resolve(_matches(_skill()))
        self.assertTrue(r.resolved)
        self.assertIsNotNone(r.skill)
        self.assertEqual(r.reason, "resolved")
        self.assertEqual(r.unsatisfied, ())

    def test_top_ranked_chosen(self):
        top = _skill(family="a", key="k1")
        low = _skill(family="b", key="k2")
        r = DependencyResolver().resolve(_matches(top, low, scores=[100, 80]))
        self.assertEqual(r.skill.registry_key, "k1")

    def test_unregistered_unsatisfied(self):
        r = DependencyResolver().resolve(_matches(_skill(status="skipped")))
        self.assertFalse(r.resolved)
        self.assertIn("registered", r.unsatisfied)

    def test_no_install_unsatisfied(self):
        r = DependencyResolver().resolve(_matches(_skill(loc="")))
        self.assertFalse(r.resolved)
        self.assertIn("installed_location", r.unsatisfied)

    def test_capability_restriction_pass(self):
        r = DependencyResolver().resolve(
            _matches(_skill(family="search")),
            available_capabilities=("search", "memory"),
        )
        self.assertTrue(r.resolved)

    def test_capability_restriction_fail(self):
        r = DependencyResolver().resolve(
            _matches(_skill(family="search")),
            available_capabilities=("memory",),
        )
        self.assertFalse(r.resolved)
        self.assertIn("search", r.unsatisfied)

    def test_fallback_to_satisfiable_candidate(self):
        bad = _skill(family="a", status="skipped", key="k1")
        good = _skill(family="b", key="k2")
        r = DependencyResolver().resolve(_matches(bad, good, scores=[100, 90]))
        self.assertTrue(r.resolved)
        self.assertEqual(r.skill.registry_key, "k2")

    def test_runtime_version_recorded_satisfied(self):
        r = DependencyResolver().resolve(_matches(_skill()), runtime_version="2.7.0")
        self.assertTrue(r.resolved)
        rv = [x for x in r.requirements if x.kind == "runtime"]
        self.assertTrue(rv and rv[0].satisfied)

    def test_permissions_recorded(self):
        r = DependencyResolver().resolve(
            _matches(_skill()), granted_permissions=("filesystem.read",)
        )
        perms = [x for x in r.requirements if x.kind == "permission"]
        self.assertTrue(perms and perms[0].satisfied)

    def test_repeatable(self):
        m = _matches(_skill())
        d = DependencyResolver()
        self.assertEqual(d.resolve(m).model_dump(), d.resolve(m).model_dump())


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
        for m in self._imports("brain/skill_runtime/dependency_resolver.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_registry_or_skill_creator(self):
        modules = self._imports("brain/skill_runtime/dependency_resolver.py")
        for banned in ["brain.skill_creator", "brain.skill_runtime.registry_discovery",
                       "core.bootstrap", "server"]:
            self.assertNotIn(banned, modules, f"resolver must not import {banned}")

    def test_no_io_tokens(self):
        modules = self._imports("brain/skill_runtime/dependency_resolver.py")
        for banned in ["subprocess", "os", "socket", "requests", "importlib"]:
            self.assertNotIn(banned, modules, f"forbidden import {banned}")
        src = (backend_dir / "brain/skill_runtime/dependency_resolver.py").read_text(encoding="utf-8")
        for banned in ["open(", "exec(", "eval(", "compile(", "__import__", ".now("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IDependencyResolver))
        self.assertTrue(c.is_registered(DependencyResolver))
        r = c.resolve(DependencyResolver).resolve(CapabilityMatchResult())
        self.assertIsInstance(r, DependencyResolution)

    def test_facade_accessor(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        from core.runtime_facade import RuntimeFacade
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertIsInstance(RuntimeFacade(c).dependency_resolver, DependencyResolver)


if __name__ == "__main__":
    unittest.main()
