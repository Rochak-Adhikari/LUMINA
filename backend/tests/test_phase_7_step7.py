"""
tests/test_phase_7_step7.py — Milestone 7.7 (Blueprint Installation)

Pipeline stage 06 — first filesystem-writing stage. BlueprintInstaller:
(ApprovalRecord, GenerationResult, target_root) -> InstallationRecord.

Verifies:
  - gated: not-approved -> installed=False, skipped_reason, no files written
  - approved -> installs; files on disk match GenerationResult.files exactly
  - idempotent reinstall -> same filesystem state + same record
  - InstallationRecord frozen, deterministic, inputs unchanged
  - full chain builder->...->approver->installer
  - import allowlist, no forbidden imports / no execution of generated code
  - dormant DI registration
"""

import ast
import tempfile
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import EvolutionRecommendation, EvolutionRecommendationSet
from brain.skill_creator.models import ApprovalRecord, GenerationResult, InstallationRecord
from brain.skill_creator.blueprint_builder import BlueprintBuilder
from brain.skill_creator.blueprint_verifier import BlueprintVerifier
from brain.skill_creator.blueprint_generator import BlueprintGenerator
from brain.skill_creator.blueprint_tester import BlueprintTester
from brain.skill_creator.blueprint_approver import BlueprintApprover
from brain.skill_creator.blueprint_installer import BlueprintInstaller
from brain.skill_creator.interfaces import IBlueprintInstaller


def _built(kind="improve_strategy", target="seq"):
    rec = EvolutionRecommendation(id="r1", kind=kind, target=target, confidence=0.5)
    s = EvolutionRecommendationSet(recommendations=[rec], recommendation_count=1)
    return BlueprintBuilder().create_blueprint(s).blueprints[0]


def _gen(bp):
    v = BlueprintVerifier().verify(bp)
    return BlueprintGenerator().generate(bp, v)


def _approval(bp, approved=True):
    return ApprovalRecord(blueprint_id=bp.id, recommendation_id=bp.recommendation_id,
                          approved=approved, approver="rochak")


class TestGate(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(BlueprintInstaller(), IBlueprintInstaller)

    def test_not_approved_blocks(self):
        bp = _built()
        with tempfile.TemporaryDirectory() as tmp:
            r = BlueprintInstaller().install(_approval(bp, approved=False), _gen(bp), tmp)
            self.assertFalse(r.installed)
            self.assertEqual(r.skipped_reason, "not_approved")
            # nothing written
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_approved_installs(self):
        bp = _built()
        with tempfile.TemporaryDirectory() as tmp:
            r = BlueprintInstaller().install(_approval(bp), _gen(bp), tmp)
            self.assertTrue(r.installed)
            self.assertEqual(r.installation_mode, "copy")


class TestFilesystem(unittest.TestCase):
    def test_files_match_generation(self):
        bp = _built("merge_memory", "notes")
        gen = _gen(bp)
        with tempfile.TemporaryDirectory() as tmp:
            r = BlueprintInstaller().install(_approval(bp), gen, tmp)
            loc = Path(r.installed_location)
            for rel, content in gen.files.items():
                self.assertTrue((loc / rel).exists(), rel)
                self.assertEqual((loc / rel).read_text(encoding="utf-8"), content)

    def test_installed_files_sorted(self):
        bp = _built()
        gen = _gen(bp)
        with tempfile.TemporaryDirectory() as tmp:
            r = BlueprintInstaller().install(_approval(bp), gen, tmp)
            self.assertEqual(r.installed_files, sorted(gen.files))

    def test_idempotent_reinstall(self):
        bp = _built()
        gen = _gen(bp)
        inst = BlueprintInstaller()
        with tempfile.TemporaryDirectory() as tmp:
            r1 = inst.install(_approval(bp), gen, tmp)
            state1 = {p.name: p.read_text(encoding="utf-8")
                      for p in Path(r1.installed_location).iterdir()}
            r2 = inst.install(_approval(bp), gen, tmp)
            state2 = {p.name: p.read_text(encoding="utf-8")
                      for p in Path(r2.installed_location).iterdir()}
            self.assertEqual(r1.model_dump(), r2.model_dump())
            self.assertEqual(state1, state2)


class TestImmutabilityDeterminism(unittest.TestCase):
    def test_record_frozen(self):
        bp = _built()
        with tempfile.TemporaryDirectory() as tmp:
            r = BlueprintInstaller().install(_approval(bp), _gen(bp), tmp)
            with self.assertRaises(Exception):
                r.installed = False

    def test_inputs_unchanged(self):
        bp = _built()
        gen = _gen(bp)
        appr = _approval(bp)
        gb, ab = gen.model_dump(), appr.model_dump()
        with tempfile.TemporaryDirectory() as tmp:
            BlueprintInstaller().install(appr, gen, tmp)
        self.assertEqual(gen.model_dump(), gb)
        self.assertEqual(appr.model_dump(), ab)

    def test_deterministic_record(self):
        bp = _built()
        gen = _gen(bp)
        inst = BlueprintInstaller()
        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
            r1 = inst.install(_approval(bp), gen, t1)
            r2 = inst.install(_approval(bp), gen, t2)
            # location differs by root; installed_files + mode + flags identical
            self.assertEqual(r1.installed_files, r2.installed_files)
            self.assertEqual(r1.installation_mode, r2.installation_mode)
            self.assertEqual(r1.installed, r2.installed)


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
                self.assertTrue(i.installed, f"{kind}:{target}")
                self.assertEqual(set(i.installed_files), set(g.files))


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
        for m in self._imports("brain/skill_creator/blueprint_installer.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_execution_tokens(self):
        # Authoritative: AST imports (subprocess/uuid/random appear in the module
        # docstring as a "no X" guarantee, not as code).
        modules = self._imports("brain/skill_creator/blueprint_installer.py")
        for banned in ["subprocess", "os", "uuid", "random", "importlib", "datetime"]:
            self.assertNotIn(banned, modules, f"forbidden import {banned}")
        src = (backend_dir / "brain/skill_creator/blueprint_installer.py").read_text(encoding="utf-8")
        for banned in ["exec(", "eval(", "compile(", "__import__", ".now(", ".system("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IBlueprintInstaller))
        bp = _built()
        with tempfile.TemporaryDirectory() as tmp:
            r = c.resolve(IBlueprintInstaller).install(_approval(bp), _gen(bp), tmp)
            self.assertTrue(r.installed)


if __name__ == "__main__":
    unittest.main()
