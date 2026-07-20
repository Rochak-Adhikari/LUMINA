"""
tests/test_phase_7_step8.py — Milestone 7.8 (Blueprint Registry)

Pipeline stage 07 — append-only catalog. BlueprintRegistry:
(InstallationRecord, SkillBlueprint) -> RegistryEntry (appended).

Verifies:
  - gated: not-installed -> registration_status="skipped", nothing appended
  - installed -> registered; entry appended
  - registry_key derived deterministically (semantic_fingerprint)
  - append-only: duplicate registration appends a NEW entry (no overwrite)
  - get() returns most-recent entry for a key
  - RegistryEntry frozen, deterministic, inputs unchanged
  - full chain builder->...->installer->registry
  - dormant DI, import allowlist, no forbidden imports
"""

import ast
import tempfile
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import EvolutionRecommendation, EvolutionRecommendationSet
from brain.skill_creator.models import InstallationRecord, RegistryEntry
from brain.skill_creator.blueprint_builder import BlueprintBuilder
from brain.skill_creator.blueprint_verifier import BlueprintVerifier
from brain.skill_creator.blueprint_generator import BlueprintGenerator
from brain.skill_creator.blueprint_tester import BlueprintTester
from brain.skill_creator.blueprint_approver import BlueprintApprover
from brain.skill_creator.blueprint_installer import BlueprintInstaller
from brain.skill_creator.blueprint_registry import BlueprintRegistry
from brain.skill_creator.interfaces import IBlueprintRegistry


def _built(kind="improve_strategy", target="seq"):
    rec = EvolutionRecommendation(id="r1", kind=kind, target=target, confidence=0.5)
    s = EvolutionRecommendationSet(recommendations=[rec], recommendation_count=1)
    return BlueprintBuilder().create_blueprint(s).blueprints[0]


def _installed(bp, loc="/skills/x"):
    return InstallationRecord(blueprint_id=bp.id, recommendation_id=bp.recommendation_id,
                              installed=True, installed_location=loc,
                              installed_files=["skill.py"], installation_mode="copy")


def _not_installed(bp):
    return InstallationRecord(blueprint_id=bp.id, recommendation_id=bp.recommendation_id,
                              installed=False, skipped_reason="not_approved")


class TestGate(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(BlueprintRegistry(), IBlueprintRegistry)

    def test_not_installed_skips(self):
        bp = _built()
        reg = BlueprintRegistry()
        e = reg.register(_not_installed(bp), bp)
        self.assertEqual(e.registration_status, "skipped")
        self.assertEqual(reg.entries(), [])  # nothing appended

    def test_installed_registers(self):
        bp = _built()
        reg = BlueprintRegistry()
        e = reg.register(_installed(bp), bp)
        self.assertEqual(e.registration_status, "registered")
        self.assertEqual(len(reg.entries()), 1)


class TestIdentity(unittest.TestCase):
    def test_registry_key_is_fingerprint(self):
        bp = _built("merge_memory", "notes")
        e = BlueprintRegistry().register(_installed(bp), bp)
        self.assertEqual(e.registry_key, bp.semantic_fingerprint)
        self.assertEqual(e.registry_key, "workspace.memory.notes.v1")

    def test_entry_carries_identity(self):
        bp = _built()
        e = BlueprintRegistry().register(_installed(bp), bp)
        self.assertEqual(e.skill_family, bp.skill_family)
        self.assertEqual(e.package_name, bp.name)
        self.assertEqual(e.blueprint_id, bp.id)


class TestAppendOnly(unittest.TestCase):
    def test_duplicate_appends_new_entry(self):
        bp = _built()
        reg = BlueprintRegistry()
        reg.register(_installed(bp, "/skills/v1"), bp)
        reg.register(_installed(bp, "/skills/v2"), bp)
        self.assertEqual(len(reg.entries()), 2)  # both kept, no overwrite

    def test_get_returns_most_recent(self):
        bp = _built()
        reg = BlueprintRegistry()
        reg.register(_installed(bp, "/skills/v1"), bp)
        reg.register(_installed(bp, "/skills/v2"), bp)
        self.assertEqual(reg.get(bp.semantic_fingerprint).installed_location, "/skills/v2")

    def test_get_missing_returns_none(self):
        self.assertIsNone(BlueprintRegistry().get("nope"))

    def test_entries_is_copy(self):
        bp = _built()
        reg = BlueprintRegistry()
        reg.register(_installed(bp), bp)
        reg.entries().append("junk")
        self.assertEqual(len(reg.entries()), 1)


class TestImmutabilityDeterminism(unittest.TestCase):
    def test_entry_frozen(self):
        bp = _built()
        e = BlueprintRegistry().register(_installed(bp), bp)
        with self.assertRaises(Exception):
            e.registration_status = "x"

    def test_deterministic_entry(self):
        bp = _built()
        e1 = BlueprintRegistry().register(_installed(bp), bp)
        e2 = BlueprintRegistry().register(_installed(bp), bp)
        self.assertEqual(e1.model_dump(), e2.model_dump())

    def test_inputs_unchanged(self):
        bp = _built()
        inst = _installed(bp)
        bpb, ib = bp.model_dump(), inst.model_dump()
        BlueprintRegistry().register(inst, bp)
        self.assertEqual(bp.model_dump(), bpb)
        self.assertEqual(inst.model_dump(), ib)


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
                e = reg.register(i, bp)
                self.assertEqual(e.registration_status, "registered", f"{kind}:{target}")
                self.assertEqual(reg.get(bp.semantic_fingerprint).blueprint_id, bp.id)


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
        for m in self._imports("brain/skill_creator/blueprint_registry.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_forbidden_tokens(self):
        modules = self._imports("brain/skill_creator/blueprint_registry.py")
        for banned in ["datetime", "uuid", "random", "os", "subprocess", "pathlib", "importlib"]:
            self.assertNotIn(banned, modules, f"forbidden import {banned}")
        src = (backend_dir / "brain/skill_creator/blueprint_registry.py").read_text(encoding="utf-8")
        for banned in ["open(", "exec(", "eval(", "compile(", "__import__", ".now("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IBlueprintRegistry))
        # dormant: empty catalog at boot, no runtime consumer
        self.assertEqual(c.resolve(IBlueprintRegistry).entries(), [])


if __name__ == "__main__":
    unittest.main()
