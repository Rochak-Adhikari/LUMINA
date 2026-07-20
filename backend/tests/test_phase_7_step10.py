"""
tests/test_phase_7_step10.py — Milestone 7.10 (Marketplace)

Pipeline stage 09 — purely descriptive manifest construction. MarketplacePublisher:
(RegistryEntry, SkillBlueprint) -> MarketplaceManifest.

Verifies:
  - interface conformance
  - registered -> published; unregistered -> skipped
  - marketplace metadata copied exactly from RegistryEntry + marketplace_identity
  - deterministic, byte-identical repeated calls
  - frozen manifest; inputs unchanged (registry/blueprint not mutated)
  - full 9-stage chain
  - no filesystem / no networking; AST import allowlist; dormant DI
"""

import ast
import tempfile
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import EvolutionRecommendation, EvolutionRecommendationSet
from brain.skill_creator.models import RegistryEntry, MarketplaceManifest
from brain.skill_creator.blueprint_builder import BlueprintBuilder
from brain.skill_creator.blueprint_verifier import BlueprintVerifier
from brain.skill_creator.blueprint_generator import BlueprintGenerator
from brain.skill_creator.blueprint_tester import BlueprintTester
from brain.skill_creator.blueprint_approver import BlueprintApprover
from brain.skill_creator.blueprint_installer import BlueprintInstaller
from brain.skill_creator.blueprint_registry import BlueprintRegistry
from brain.skill_creator.lifecycle_manager import LifecycleManager
from brain.skill_creator.marketplace_publisher import MarketplacePublisher
from brain.skill_creator.interfaces import IMarketplacePublisher


def _built(kind="merge_memory", target="notes"):
    rec = EvolutionRecommendation(id="r1", kind=kind, target=target, confidence=0.5)
    s = EvolutionRecommendationSet(recommendations=[rec], recommendation_count=1)
    return BlueprintBuilder().create_blueprint(s).blueprints[0]


def _entry(bp, status="registered"):
    return RegistryEntry(
        blueprint_id=bp.id, recommendation_id=bp.recommendation_id,
        semantic_fingerprint=bp.semantic_fingerprint, skill_family=bp.skill_family,
        package_name=bp.name, registry_key=bp.semantic_fingerprint,
        installed_location="/skills/x", registration_status=status,
    )


class TestGate(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(MarketplacePublisher(), IMarketplacePublisher)

    def test_registered_published(self):
        bp = _built()
        m = MarketplacePublisher().publish(_entry(bp), bp)
        self.assertEqual(m.manifest_status, "published")

    def test_unregistered_skipped(self):
        bp = _built()
        m = MarketplacePublisher().publish(_entry(bp, status="skipped"), bp)
        self.assertEqual(m.manifest_status, "skipped")


class TestContent(unittest.TestCase):
    def setUp(self):
        self.bp = _built()
        self.m = MarketplacePublisher().publish(_entry(self.bp), self.bp)

    def test_identity_copied(self):
        self.assertEqual(self.m.registry_key, self.bp.semantic_fingerprint)
        self.assertEqual(self.m.semantic_fingerprint, self.bp.semantic_fingerprint)
        self.assertEqual(self.m.skill_family, self.bp.skill_family)
        self.assertEqual(self.m.package_name, self.bp.name)

    def test_marketplace_identity_copied(self):
        ident = self.bp.marketplace_identity
        self.assertEqual(self.m.tags, ident.marketplace_tags)
        self.assertEqual(self.m.categories, (ident.compatibility_family,))

    def test_title_and_version(self):
        self.assertEqual(self.m.title, self.bp.name)
        self.assertEqual(self.m.version, self.bp.version)

    def test_no_invented_values(self):
        # empty blueprint metadata -> empty manifest fields (nothing fabricated)
        self.assertEqual(self.m.homepage, "")
        self.assertEqual(self.m.repository, "")
        self.assertEqual(self.m.license, "")


class TestDeterminismImmutability(unittest.TestCase):
    def test_byte_identical_repeat(self):
        bp = _built()
        e = _entry(bp)
        p = MarketplacePublisher()
        self.assertEqual(p.publish(e, bp).model_dump(), p.publish(e, bp).model_dump())

    def test_frozen(self):
        bp = _built()
        m = MarketplacePublisher().publish(_entry(bp), bp)
        with self.assertRaises(Exception):
            m.manifest_status = "x"

    def test_inputs_unchanged(self):
        bp = _built()
        e = _entry(bp)
        bpb, eb = bp.model_dump(), e.model_dump()
        MarketplacePublisher().publish(e, bp)
        self.assertEqual(bp.model_dump(), bpb)
        self.assertEqual(e.model_dump(), eb)


class TestIntegration(unittest.TestCase):
    def test_full_chain(self):
        for kind, target in [("improve_strategy", "seq"),
                             ("merge_memory", "notes"),
                             ("future_skill_candidate", "web")]:
            bp = _built(kind, target)
            v = BlueprintVerifier().verify(bp)
            g = BlueprintGenerator().generate(bp, v)
            t = BlueprintTester().test(bp, g)
            a = BlueprintApprover().review(t, approver="rochak", approve=True)
            with tempfile.TemporaryDirectory() as tmp:
                i = BlueprintInstaller().install(a, g, tmp)
                reg = BlueprintRegistry()
                entry = reg.register(i, bp)
                lc = LifecycleManager()
                lc.transition(entry, "activate")
                # registry + lifecycle unchanged by marketplace
                before_entries = len(reg.entries())
                before_events = len(lc.events())
                man = MarketplacePublisher().publish(entry, bp)
                self.assertEqual(man.manifest_status, "published", f"{kind}:{target}")
                self.assertEqual(len(reg.entries()), before_entries)
                self.assertEqual(len(lc.events()), before_events)


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
            "brain.skill_creator.models",
            "brain.skill_creator.interfaces",
            "typing", "__future__",
        )
        for m in self._imports("brain/skill_creator/marketplace_publisher.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_networking_or_io(self):
        modules = self._imports("brain/skill_creator/marketplace_publisher.py")
        for banned in ["requests", "socket", "http", "urllib", "os", "subprocess",
                       "pathlib", "importlib", "datetime", "uuid", "random"]:
            self.assertNotIn(banned, modules, f"forbidden import {banned}")
        src = (backend_dir / "brain/skill_creator/marketplace_publisher.py").read_text(encoding="utf-8")
        for banned in ["open(", "exec(", "eval(", "compile(", "__import__", ".now("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IMarketplacePublisher))
        bp = _built()
        m = c.resolve(IMarketplacePublisher).publish(_entry(bp), bp)
        self.assertEqual(m.manifest_status, "published")


if __name__ == "__main__":
    unittest.main()
