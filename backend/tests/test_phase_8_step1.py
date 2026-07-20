"""
tests/test_phase_8_step1.py — Milestone 8.1 Verification (Registry Discovery)

First Phase 8 stage. RegistryDiscovery: read-only projection of the frozen
Phase 7 registry into DiscoveredSkill / RegistrySearchResult.

Verifies:
  - models frozen, serializable, metadata-only (no executable payload)
  - discover() lists registered skills; empty query = everything
  - only "registered" entries visible (skipped/unregistered hidden)
  - supersession WITHOUT mutation: latest registered entry per key wins
  - deterministic ordering (family, package, key) regardless of insert order
  - substring query over family/package/fingerprint, case-insensitive
  - discovery never mutates the registry (append-only catalog untouched)
  - duck-typed registry (only .entries() used) — no BlueprintRegistry import
  - import allowlist; no execution tokens
  - dormant DI registration via bootstrap + facade accessor
  - full chain builder->...->registry->discovery

Stdlib unittest; heavy deps mocked where needed.
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.skill_runtime.models import DiscoveredSkill, RegistrySearchResult
from brain.skill_runtime.interfaces import IRegistryDiscovery
from brain.skill_runtime.registry_discovery import RegistryDiscovery


class _Entry:
    """RegistryEntry stand-in (duck-typed — only attributes are read)."""
    def __init__(self, key, family="fam", package="pkg", fp="fp",
                 status="registered", loc="/x", bid="b", rid="r"):
        self.registry_key = key
        self.skill_family = family
        self.package_name = package
        self.semantic_fingerprint = fp
        self.registration_status = status
        self.installed_location = loc
        self.blueprint_id = bid
        self.recommendation_id = rid


class _FakeRegistry:
    def __init__(self, entries):
        self._entries = list(entries)
        self.entries_calls = 0

    def entries(self):
        self.entries_calls += 1
        return list(self._entries)


class TestModels(unittest.TestCase):
    def test_frozen(self):
        d = DiscoveredSkill(blueprint_id="b")
        with self.assertRaises(Exception):
            d.package_name = "y"
        r = RegistrySearchResult()
        with self.assertRaises(Exception):
            r.total_count = 9

    def test_serializable(self):
        import json
        r = RegistrySearchResult(
            skills=[DiscoveredSkill(blueprint_id="b", package_name="p")],
            total_count=1, query="p",
        )
        json.dumps(r.model_dump())

    def test_metadata_only(self):
        d = DiscoveredSkill(blueprint_id="b")
        self.assertFalse(any(callable(v) for v in d.model_dump().values()))


class TestDiscovery(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(RegistryDiscovery(_FakeRegistry([])), IRegistryDiscovery)

    def test_empty_query_lists_all(self):
        reg = _FakeRegistry([_Entry("k1"), _Entry("k2", package="pkg2")])
        r = RegistryDiscovery(reg).discover()
        self.assertEqual(r.total_count, 2)
        self.assertEqual(r.query, "")

    def test_only_registered_visible(self):
        reg = _FakeRegistry([
            _Entry("k1"),
            _Entry("k2", status="skipped"),
            _Entry("k3", status="unregistered"),
        ])
        r = RegistryDiscovery(reg).discover()
        self.assertEqual(r.total_count, 1)
        self.assertEqual(r.skills[0].registry_key, "k1")

    def test_supersession_latest_wins_no_mutation(self):
        # same key twice: last appended registered entry wins
        reg = _FakeRegistry([
            _Entry("k1", package="old"),
            _Entry("k1", package="new"),
        ])
        r = RegistryDiscovery(reg).discover()
        self.assertEqual(r.total_count, 1)
        self.assertEqual(r.skills[0].package_name, "new")
        # registry untouched (still 2 raw entries)
        self.assertEqual(len(reg._entries), 2)

    def test_superseding_registered_over_skipped(self):
        # latest is skipped -> that key hidden entirely (matches get() semantics:
        # most-recent appended wins; if it's not registered, nothing shows)
        reg = _FakeRegistry([
            _Entry("k1", package="ok"),
            _Entry("k1", package="bad", status="skipped"),
        ])
        r = RegistryDiscovery(reg).discover()
        self.assertEqual(r.total_count, 0)

    def test_deterministic_order(self):
        reg = _FakeRegistry([
            _Entry("k3", family="z", package="p"),
            _Entry("k1", family="a", package="p"),
            _Entry("k2", family="m", package="p"),
        ])
        r = RegistryDiscovery(reg).discover()
        self.assertEqual([s.skill_family for s in r.skills], ["a", "m", "z"])

    def test_query_substring_case_insensitive(self):
        reg = _FakeRegistry([
            _Entry("k1", family="WebSearch"),
            _Entry("k2", family="Notes"),
        ])
        r = RegistryDiscovery(reg).discover("web")
        self.assertEqual(r.total_count, 1)
        self.assertEqual(r.skills[0].skill_family, "WebSearch")
        self.assertEqual(r.query, "web")

    def test_query_matches_package_and_fingerprint(self):
        reg = _FakeRegistry([
            _Entry("k1", family="f", package="alpha", fp="zzz"),
            _Entry("k2", family="f", package="beta", fp="target9"),
        ])
        d = RegistryDiscovery(reg)
        self.assertEqual(d.discover("alpha").total_count, 1)
        self.assertEqual(d.discover("target9").total_count, 1)

    def test_no_match_empty_result(self):
        reg = _FakeRegistry([_Entry("k1", family="f")])
        r = RegistryDiscovery(reg).discover("nonexistent")
        self.assertEqual(r.total_count, 0)
        self.assertEqual(r.skills, [])

    def test_duck_typed_only_entries(self):
        reg = _FakeRegistry([_Entry("k1")])
        RegistryDiscovery(reg).discover()
        self.assertEqual(reg.entries_calls, 1)


class TestIntegration(unittest.TestCase):
    def test_full_chain_builder_to_discovery(self):
        import tempfile
        from brain.evolution.models import (
            EvolutionRecommendation, EvolutionRecommendationSet)
        from brain.skill_creator.blueprint_builder import BlueprintBuilder
        from brain.skill_creator.blueprint_verifier import BlueprintVerifier
        from brain.skill_creator.blueprint_generator import BlueprintGenerator
        from brain.skill_creator.blueprint_installer import BlueprintInstaller
        from brain.skill_creator.blueprint_registry import BlueprintRegistry
        from brain.skill_creator.models import ApprovalRecord

        rec = EvolutionRecommendation(id="r1", kind="improve_strategy", target="seq")
        s = EvolutionRecommendationSet(recommendations=[rec], recommendation_count=1)
        bp = BlueprintBuilder().create_blueprint(s).blueprints[0]
        v = BlueprintVerifier().verify(bp)
        gen = BlueprintGenerator().generate(bp, v)
        appr = ApprovalRecord(blueprint_id=bp.id, recommendation_id=bp.recommendation_id,
                              approved=True, approver="rochak")
        reg = BlueprintRegistry()
        with tempfile.TemporaryDirectory() as tmp:
            inst = BlueprintInstaller().install(appr, gen, tmp)
            reg.register(inst, bp)
        r = RegistryDiscovery(reg).discover()
        self.assertEqual(r.total_count, 1)
        self.assertEqual(r.skills[0].registry_key, bp.semantic_fingerprint)


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
            "pydantic", "typing", "abc", "__future__",
        )
        for rel in ["brain/skill_runtime/models.py",
                    "brain/skill_runtime/interfaces.py",
                    "brain/skill_runtime/registry_discovery.py",
                    "brain/skill_runtime/__init__.py"]:
            for m in self._imports(rel):
                self.assertTrue(m.startswith(allowed), f"{rel}: forbidden import {m}")

    def test_no_upward_skill_creator_import(self):
        # discovery is duck-typed; must NOT import the concrete registry class
        for rel in ["brain/skill_runtime/registry_discovery.py",
                    "brain/skill_runtime/models.py",
                    "brain/skill_runtime/interfaces.py"]:
            for m in self._imports(rel):
                self.assertFalse(m.startswith("brain.skill_creator"),
                                 f"{rel} must not import skill_creator ({m})")

    def test_no_execution_tokens(self):
        for rel in ["brain/skill_runtime/models.py",
                    "brain/skill_runtime/interfaces.py",
                    "brain/skill_runtime/registry_discovery.py"]:
            src = (backend_dir / rel).read_text(encoding="utf-8")
            for banned in ["subprocess", "os.system", "exec(", "eval(",
                           "compile(", "__import__", "importlib", "uuid",
                           "random", ".now("]:
                self.assertNotIn(banned, src, f"{rel}: forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IRegistryDiscovery))
        self.assertTrue(c.is_registered(RegistryDiscovery))
        # resolvable (concrete, dormant) and read-only over the registry
        disc = c.resolve(RegistryDiscovery)
        self.assertIsInstance(disc.discover(), RegistrySearchResult)

    def test_facade_accessor(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        from core.runtime_facade import RuntimeFacade
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        f = RuntimeFacade(c)
        self.assertIsInstance(f.registry_discovery, RegistryDiscovery)


if __name__ == "__main__":
    unittest.main()
