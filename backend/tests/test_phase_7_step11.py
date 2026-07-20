"""
tests/test_phase_7_step11.py — Milestone 7.11 (Rollback) — final pipeline stage

RollbackManager: (InstallationRecord, SkillBlueprint) -> RollbackRecord.

Verifies:
  - interface conformance
  - not-installed -> skipped (no filesystem ops)
  - installed -> rollback performed; installer-created files removed
  - unrelated files left untouched
  - empty directories pruned
  - idempotent repeated rollback (same fs state)
  - RollbackRecord frozen, deterministic, inputs unchanged
  - full 10-stage pipeline (registry/lifecycle/marketplace not mutated)
  - import allowlist, AST forbidden-import check, dormant DI
"""

import ast
import tempfile
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import EvolutionRecommendation, EvolutionRecommendationSet
from brain.skill_creator.models import RollbackRecord
from brain.skill_creator.blueprint_builder import BlueprintBuilder
from brain.skill_creator.blueprint_verifier import BlueprintVerifier
from brain.skill_creator.blueprint_generator import BlueprintGenerator
from brain.skill_creator.blueprint_tester import BlueprintTester
from brain.skill_creator.blueprint_approver import BlueprintApprover
from brain.skill_creator.blueprint_installer import BlueprintInstaller
from brain.skill_creator.blueprint_registry import BlueprintRegistry
from brain.skill_creator.lifecycle_manager import LifecycleManager
from brain.skill_creator.marketplace_publisher import MarketplacePublisher
from brain.skill_creator.rollback_manager import RollbackManager
from brain.skill_creator.interfaces import IRollbackManager


def _built(kind="merge_memory", target="notes"):
    rec = EvolutionRecommendation(id="r1", kind=kind, target=target, confidence=0.5)
    s = EvolutionRecommendationSet(recommendations=[rec], recommendation_count=1)
    return BlueprintBuilder().create_blueprint(s).blueprints[0]


def _install(bp, root):
    v = BlueprintVerifier().verify(bp)
    g = BlueprintGenerator().generate(bp, v)
    t = BlueprintTester().test(bp, g)
    a = BlueprintApprover().review(t, approver="rochak", approve=True)
    return BlueprintInstaller().install(a, g, root)


class TestGate(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(RollbackManager(), IRollbackManager)

    def test_not_installed_skipped(self):
        from brain.skill_creator.models import InstallationRecord
        bp = _built()
        inst = InstallationRecord(blueprint_id=bp.id, installed=False, skipped_reason="x")
        r = RollbackManager().rollback(inst, bp)
        self.assertFalse(r.rollback_performed)
        self.assertEqual(r.rollback_status, "skipped")
        self.assertEqual(r.skipped_reason, "not_installed")


class TestRollback(unittest.TestCase):
    def test_installed_rolls_back(self):
        bp = _built()
        with tempfile.TemporaryDirectory() as tmp:
            inst = _install(bp, tmp)
            r = RollbackManager().rollback(inst, bp)
            self.assertTrue(r.rollback_performed)
            self.assertEqual(r.rollback_status, "rolled_back")
            # every installed file gone
            for rel in inst.installed_files:
                self.assertFalse((Path(inst.installed_location) / rel).exists())
            self.assertEqual(sorted(r.removed_files), sorted(inst.installed_files))

    def test_unrelated_files_untouched(self):
        bp = _built()
        with tempfile.TemporaryDirectory() as tmp:
            inst = _install(bp, tmp)
            # place an unrelated file in the install dir
            other = Path(inst.installed_location) / "KEEP.txt"
            other.write_text("keep me", encoding="utf-8")
            RollbackManager().rollback(inst, bp)
            self.assertTrue(other.exists())

    def test_empty_dirs_pruned(self):
        bp = _built()
        with tempfile.TemporaryDirectory() as tmp:
            inst = _install(bp, tmp)
            RollbackManager().rollback(inst, bp)
            # install location removed (all installer files gone, nothing else)
            self.assertFalse(Path(inst.installed_location).exists())

    def test_idempotent(self):
        bp = _built()
        with tempfile.TemporaryDirectory() as tmp:
            inst = _install(bp, tmp)
            rb = RollbackManager()
            r1 = rb.rollback(inst, bp)
            r2 = rb.rollback(inst, bp)  # already gone
            self.assertTrue(r1.rollback_performed)
            self.assertTrue(r2.rollback_performed)
            self.assertEqual(r2.removed_files, [])  # nothing left to remove
            self.assertFalse(Path(inst.installed_location).exists())


class TestImmutabilityDeterminism(unittest.TestCase):
    def test_frozen(self):
        bp = _built()
        with tempfile.TemporaryDirectory() as tmp:
            inst = _install(bp, tmp)
            r = RollbackManager().rollback(inst, bp)
            with self.assertRaises(Exception):
                r.rollback_performed = False

    def test_inputs_unchanged(self):
        bp = _built()
        with tempfile.TemporaryDirectory() as tmp:
            inst = _install(bp, tmp)
            bpb, ib = bp.model_dump(), inst.model_dump()
            RollbackManager().rollback(inst, bp)
            self.assertEqual(bp.model_dump(), bpb)
            self.assertEqual(inst.model_dump(), ib)

    def test_deterministic_removed_files(self):
        bp = _built()
        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
            i1 = _install(bp, t1)
            i2 = _install(bp, t2)
            r1 = RollbackManager().rollback(i1, bp)
            r2 = RollbackManager().rollback(i2, bp)
            self.assertEqual(r1.removed_files, r2.removed_files)
            self.assertEqual(r1.rollback_status, r2.rollback_status)


class TestIntegration(unittest.TestCase):
    def test_full_pipeline(self):
        for kind, target in [("improve_strategy", "seq"),
                             ("merge_memory", "notes"),
                             ("future_skill_candidate", "web")]:
            bp = _built(kind, target)
            with tempfile.TemporaryDirectory() as tmp:
                inst = _install(bp, tmp)
                reg = BlueprintRegistry()
                entry = reg.register(inst, bp)
                lc = LifecycleManager()
                lc.transition(entry, "activate")
                man = MarketplacePublisher().publish(entry, bp)
                before = (len(reg.entries()), len(lc.events()), man.manifest_status)
                r = RollbackManager().rollback(inst, bp)
                self.assertTrue(r.rollback_performed, f"{kind}:{target}")
                # rollback never mutates registry/lifecycle/marketplace
                self.assertEqual(len(reg.entries()), before[0])
                self.assertEqual(len(lc.events()), before[1])
                self.assertEqual(man.manifest_status, before[2])


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
            "pathlib", "typing", "__future__",
        )
        for m in self._imports("brain/skill_creator/rollback_manager.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_forbidden_imports(self):
        modules = self._imports("brain/skill_creator/rollback_manager.py")
        for banned in ["os", "subprocess", "importlib", "datetime", "uuid",
                       "random", "requests", "socket", "http"]:
            self.assertNotIn(banned, modules, f"forbidden import {banned}")
        src = (backend_dir / "brain/skill_creator/rollback_manager.py").read_text(encoding="utf-8")
        for banned in ["exec(", "eval(", "compile(", "__import__", ".now(", "shutil"]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IRollbackManager))
        bp = _built()
        with tempfile.TemporaryDirectory() as tmp:
            inst = _install(bp, tmp)
            r = c.resolve(IRollbackManager).rollback(inst, bp)
            self.assertTrue(r.rollback_performed)


if __name__ == "__main__":
    unittest.main()
