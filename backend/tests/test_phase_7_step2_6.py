"""
tests/test_phase_7_step2_6.py — Milestone 7.2.6 (SkillBlueprint Schema Freeze)

Final schema-freeze verification. Reserved contract declarations exist; blueprint
stays frozen, deterministic, serializable, metadata only.

Verifies:
  - reserved contracts present (expected_quality_dimensions, verification_contract,
    generation_contract, installation_contract, marketplace_identity)
  - sub-contract models frozen + serializable
  - blueprint frozen; deterministic byte-identical construction
  - no executable payload / no runtime/installer/validator/compiler imports
  - no subprocess/eval/exec/compile/__import__/filesystem in the package
  - builder populates marketplace_identity deterministically

Stdlib unittest.
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import EvolutionRecommendation, EvolutionRecommendationSet
from brain.skill_creator.models import (
    SkillBlueprint,
    VerificationContract,
    GenerationContract,
    InstallationContract,
    MarketplaceIdentity,
)
from brain.skill_creator.blueprint_builder import BlueprintBuilder


def _bp(**kw):
    base = dict(id="bp:x", recommendation_id="r1")
    base.update(kw)
    return SkillBlueprint(**base)


def _built(kind="merge_memory", target="notes"):
    rec = EvolutionRecommendation(id="r1", kind=kind, target=target, confidence=0.5)
    s = EvolutionRecommendationSet(recommendations=[rec], recommendation_count=1)
    return BlueprintBuilder().create_blueprint(s).blueprints[0]


class TestReservedContracts(unittest.TestCase):
    def test_expected_quality_dimensions(self):
        dims = _bp().expected_quality_dimensions
        self.assertIn("correctness", dims)
        self.assertIn("security", dims)
        self.assertIsInstance(dims, tuple)

    def test_verification_contract_present(self):
        vc = _bp().verification_contract
        self.assertIsInstance(vc, VerificationContract)
        self.assertIn("schema", vc.expected_checks)

    def test_generation_contract_present(self):
        gc = _bp().generation_contract
        self.assertIsInstance(gc, GenerationContract)
        self.assertEqual(gc.expected_manifest_version, "1.0")

    def test_installation_contract_present(self):
        ic = _bp().installation_contract
        self.assertIsInstance(ic, InstallationContract)
        self.assertEqual(ic.activation_strategy, "manual_approval")

    def test_marketplace_identity_present(self):
        mi = _bp().marketplace_identity
        self.assertIsInstance(mi, MarketplaceIdentity)
        self.assertEqual(mi.semantic_version_strategy, "semver")


class TestSubModelsFrozen(unittest.TestCase):
    def test_all_frozen(self):
        for m in (VerificationContract, GenerationContract, InstallationContract, MarketplaceIdentity):
            self.assertTrue(m.model_config.get("frozen"), m.__name__)

    def test_instances_immutable(self):
        vc = VerificationContract()
        with self.assertRaises(Exception):
            vc.expected_checks = ()

    def test_serializable(self):
        import json
        json.dumps(_bp().model_dump())


class TestDeterminism(unittest.TestCase):
    def test_blueprint_byte_identical(self):
        self.assertEqual(_bp().model_dump(), _bp().model_dump())

    def test_builder_populates_marketplace(self):
        mi = _built("merge_memory", "notes").marketplace_identity
        self.assertEqual(mi.exportable_identity, "workspace.memory.notes.v1")
        self.assertEqual(mi.compatibility_family, "workspace.memory")

    def test_builder_byte_identical(self):
        self.assertEqual(_built().model_dump(), _built().model_dump())


class TestNoBehavior(unittest.TestCase):
    def test_blueprint_frozen(self):
        with self.assertRaises(Exception):
            _bp().status = "installed"

    def test_no_methods_on_blueprint(self):
        # blueprint is data only — no custom callables beyond pydantic machinery
        custom = [n for n in vars(SkillBlueprint)
                  if not n.startswith("_") and callable(getattr(SkillBlueprint, n))
                  and n not in dir(__import__("pydantic").BaseModel)]
        self.assertEqual(custom, [])

    def _pkg_files(self):
        return [
            "brain/skill_creator/models.py",
            "brain/skill_creator/interfaces.py",
            "brain/skill_creator/blueprint_builder.py",
            "brain/skill_creator/__init__.py",
        ]

    def test_no_executable_payload(self):
        for rel in self._pkg_files():
            src = (backend_dir / rel).read_text(encoding="utf-8")
            for banned in ["subprocess", "os.system", "exec(", "eval(",
                           "compile(", "__import__", "open("]:
                self.assertNotIn(banned, src, f"{rel}: forbidden {banned}")

    def test_no_forbidden_imports(self):
        for rel in self._pkg_files():
            src = (backend_dir / rel).read_text(encoding="utf-8")
            modules = set()
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    modules.add(node.module)
                elif isinstance(node, ast.Import):
                    modules.update(a.name for a in node.names)
            for banned in [
                "brain.core.brain_core", "core.runtime_facade", "core.bootstrap",
                "brain.planning.rule_planner", "brain.planning.llm_planner",
                "brain.workspace.memory", "brain.reflection.engine",
                "brain.skills.registry", "server", "subprocess", "os",
            ]:
                self.assertNotIn(banned, modules, f"{rel}: forbidden import {banned}")


if __name__ == "__main__":
    unittest.main()
