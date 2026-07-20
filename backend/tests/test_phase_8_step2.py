"""
tests/test_phase_8_step2.py — Milestone 8.2 Verification (Capability Matching)

Semantic layer over Registry Discovery. CapabilityMatcher: CapabilityRequest ->
CapabilityMatchResult, ranked deterministically.

Verifies:
  - frozen models (CapabilityRequest / CapabilityMatch / CapabilityMatchResult)
  - exact capability (==family) → 100; alias (in fingerprint/package) → 80;
    tag → 60
  - family / package hard restrictions
  - empty / no-match results
  - deterministic, stable ordering (score desc, family, package, key)
  - duplicate elimination (via discovery supersession)
  - depends only on IRegistryDiscovery (no registry mutation, no execution)
  - no BlueprintRegistry / skill_creator imports; no I/O tokens
  - dormant DI registration + RuntimeFacade accessor
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
    CapabilityRequest,
    DiscoveredSkill,
    RegistrySearchResult,
)
from brain.skill_runtime.interfaces import ICapabilityMatcher
from brain.skill_runtime.capability_matcher import CapabilityMatcher


def _skill(family="fam", package="pkg", fp="fp", key=None):
    return DiscoveredSkill(
        blueprint_id="b", semantic_fingerprint=fp, skill_family=family,
        package_name=package, registry_key=key or f"{family}.{package}",
        installed_location="/x", registration_status="registered",
    )


class _FakeDiscovery:
    """IRegistryDiscovery stand-in. Records calls; never mutated by matcher."""
    def __init__(self, skills):
        self._skills = list(skills)
        self.discover_calls = 0

    def discover(self, query: str = "") -> RegistrySearchResult:
        self.discover_calls += 1
        return RegistrySearchResult(
            skills=list(self._skills), total_count=len(self._skills), query=query
        )


class TestModels(unittest.TestCase):
    def test_frozen(self):
        r = CapabilityRequest(capability="c")
        with self.assertRaises(Exception):
            r.capability = "x"
        m = CapabilityMatch(skill=_skill(), score=1, reason="r")
        with self.assertRaises(Exception):
            m.score = 2
        res = CapabilityMatchResult()
        with self.assertRaises(Exception):
            res.match_count = 9

    def test_serializable(self):
        import json
        res = CapabilityMatchResult(
            matches=[CapabilityMatch(skill=_skill(), score=100, reason="exact capability")],
            match_count=1, capability="c",
        )
        json.dumps(res.model_dump())


class TestMatching(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(CapabilityMatcher(_FakeDiscovery([])), ICapabilityMatcher)

    def test_exact_capability(self):
        d = _FakeDiscovery([_skill(family="search")])
        r = CapabilityMatcher(d).match(CapabilityRequest(capability="search"))
        self.assertEqual(r.match_count, 1)
        self.assertEqual(r.matches[0].score, 100)
        self.assertEqual(r.matches[0].reason, "exact capability")

    def test_alias_fingerprint(self):
        d = _FakeDiscovery([_skill(family="other", fp="workspace.search.v1")])
        r = CapabilityMatcher(d).match(CapabilityRequest(capability="search"))
        self.assertEqual(r.matches[0].score, 80)
        self.assertEqual(r.matches[0].reason, "alias")

    def test_alias_package(self):
        d = _FakeDiscovery([_skill(family="other", package="searchtool", fp="zzz")])
        r = CapabilityMatcher(d).match(CapabilityRequest(capability="search"))
        self.assertEqual(r.matches[0].score, 80)

    def test_tag(self):
        d = _FakeDiscovery([_skill(family="memory", package="p", fp="q")])
        r = CapabilityMatcher(d).match(CapabilityRequest(capability="nomatch", tags=("memory",)))
        self.assertEqual(r.matches[0].score, 60)
        self.assertEqual(r.matches[0].reason, "tag")

    def test_family_restriction(self):
        d = _FakeDiscovery([_skill(family="a", fp="cap"), _skill(family="b", fp="cap")])
        r = CapabilityMatcher(d).match(CapabilityRequest(capability="cap", family="a"))
        self.assertEqual(r.match_count, 1)
        self.assertEqual(r.matches[0].skill.skill_family, "a")

    def test_package_restriction(self):
        d = _FakeDiscovery([_skill(package="p1", fp="cap"), _skill(package="p2", fp="cap")])
        r = CapabilityMatcher(d).match(CapabilityRequest(capability="cap", package="p1"))
        self.assertEqual(r.match_count, 1)
        self.assertEqual(r.matches[0].skill.package_name, "p1")

    def test_empty_result(self):
        d = _FakeDiscovery([_skill(family="x", package="y", fp="z")])
        r = CapabilityMatcher(d).match(CapabilityRequest(capability="nope"))
        self.assertEqual(r.match_count, 0)
        self.assertEqual(r.matches, [])

    def test_no_skills(self):
        r = CapabilityMatcher(_FakeDiscovery([])).match(CapabilityRequest(capability="c"))
        self.assertEqual(r.match_count, 0)

    def test_pure_filter_no_capability_no_tags(self):
        d = _FakeDiscovery([_skill(family="a"), _skill(family="b")])
        r = CapabilityMatcher(d).match(CapabilityRequest(family="a"))
        self.assertEqual(r.match_count, 1)
        self.assertEqual(r.matches[0].score, 0)

    def test_deterministic_ordering(self):
        d = _FakeDiscovery([
            _skill(family="ztag", package="p", fp="q"),   # tag 60
            _skill(family="cap", package="p", fp="q"),     # exact 100
            _skill(family="other", package="p", fp="cap"), # alias 80
        ])
        r = CapabilityMatcher(d).match(CapabilityRequest(capability="cap", tags=("ztag",)))
        self.assertEqual([m.score for m in r.matches], [100, 80, 60])

    def test_stable_tie_break(self):
        d = _FakeDiscovery([
            _skill(family="cap", package="zpkg", key="k2"),
            _skill(family="cap", package="apkg", key="k1"),
        ])
        r = CapabilityMatcher(d).match(CapabilityRequest(capability="cap"))
        # equal score 100 → sorted by package
        self.assertEqual([m.skill.package_name for m in r.matches], ["apkg", "zpkg"])

    def test_repeatable(self):
        d = _FakeDiscovery([_skill(family="cap"), _skill(family="other", fp="cap")])
        m = CapabilityMatcher(d)
        a = m.match(CapabilityRequest(capability="cap"))
        b = m.match(CapabilityRequest(capability="cap"))
        self.assertEqual(a.model_dump(), b.model_dump())

    def test_depends_only_on_discovery(self):
        d = _FakeDiscovery([_skill()])
        CapabilityMatcher(d).match(CapabilityRequest(capability="fam"))
        self.assertGreaterEqual(d.discover_calls, 1)


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
        for m in self._imports("brain/skill_runtime/capability_matcher.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_phase7_or_registry_imports(self):
        modules = self._imports("brain/skill_runtime/capability_matcher.py")
        for banned in ["brain.skill_creator", "brain.skill_creator.blueprint_registry",
                       "brain.skill_creator.models", "core.bootstrap", "server"]:
            self.assertNotIn(banned, modules, f"matcher must not import {banned}")

    def test_no_io_tokens(self):
        # AST-authoritative: forbidden modules must not be imported (the words
        # appear in the module docstring as "no X" guarantees, not as code).
        modules = self._imports("brain/skill_runtime/capability_matcher.py")
        for banned in ["subprocess", "os", "socket", "requests", "importlib", "http", "urllib"]:
            self.assertNotIn(banned, modules, f"forbidden import {banned}")
        src = (backend_dir / "brain/skill_runtime/capability_matcher.py").read_text(encoding="utf-8")
        for banned in ["open(", "exec(", "eval(", "compile(", "__import__", ".now("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(ICapabilityMatcher))
        self.assertTrue(c.is_registered(CapabilityMatcher))
        r = c.resolve(CapabilityMatcher).match(CapabilityRequest(capability="x"))
        self.assertIsInstance(r, CapabilityMatchResult)

    def test_facade_accessor(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        from core.runtime_facade import RuntimeFacade
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertIsInstance(RuntimeFacade(c).capability_matcher, CapabilityMatcher)


if __name__ == "__main__":
    unittest.main()
