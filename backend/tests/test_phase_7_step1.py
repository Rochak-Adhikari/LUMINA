"""
tests/test_phase_7_step1.py — Milestone 7.1 Verification (Skill Creator Foundation)

Verifies foundation contracts only:

  - SkillBlueprint / SkillBlueprintSet / SkillGenerationRequest /
    SkillGenerationResult: frozen, primitive, serializable
  - status defaults to "draft" (never executable)
  - reserved extension fields present (version, dependencies, required_tools,
    required_permissions, estimated_runtime, risk_level, rollback_strategy,
    verification_requirements) with no behavior
  - ISkillCreator contract shape (create_blueprint only)
  - no forbidden imports / no runtime references / no executable payload
  - ISkillCreator registered dormant (present, never resolved)

Stdlib unittest; no heavy deps.
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import (
    EvolutionRecommendation,
    EvolutionRecommendationSet,
)
from brain.skill_creator.models import (
    SkillBlueprint,
    SkillBlueprintSet,
    SkillGenerationRequest,
    SkillGenerationResult,
)
from brain.skill_creator.interfaces import ISkillCreator


class TestModels(unittest.TestCase):
    def test_blueprint_frozen(self):
        b = SkillBlueprint(id="x", recommendation_id="r0")
        with self.assertRaises(Exception):
            b.status = "active"

    def test_status_default_draft(self):
        self.assertEqual(SkillBlueprint(id="x", recommendation_id="r0").status, "draft")

    def test_reserved_extension_fields_present(self):
        b = SkillBlueprint(id="x", recommendation_id="r0")
        for field in [
            "version", "dependencies", "required_tools", "required_permissions",
            "estimated_runtime", "risk_level", "rollback_strategy",
            "verification_requirements",
        ]:
            self.assertIn(field, b.model_fields, f"reserved field missing: {field}")

    def test_all_models_frozen(self):
        for m in (SkillBlueprint, SkillBlueprintSet, SkillGenerationRequest, SkillGenerationResult):
            self.assertTrue(m.model_config.get("frozen"), m.__name__)

    def test_serializable(self):
        import json
        b = SkillBlueprint(id="b1", recommendation_id="r1", name="demo", source_recommendation_ids=["r1"])
        s = SkillBlueprintSet(blueprints=[b], blueprint_count=1)
        json.dumps(s.model_dump())
        recs = EvolutionRecommendationSet(
            recommendations=[EvolutionRecommendation(id="r1", kind="future_skill_candidate")],
            recommendation_count=1,
        )
        req = SkillGenerationRequest(recommendations=recs, approved=False)
        json.dumps(req.model_dump())
        json.dumps(SkillGenerationResult(accepted=["r1"], rejected=[], reason="ok").model_dump())

    def test_request_carries_recommendations_and_approval(self):
        recs = EvolutionRecommendationSet(recommendations=[], recommendation_count=0)
        req = SkillGenerationRequest(recommendations=recs, approved_by="rochak", approved=True)
        self.assertTrue(req.approved)
        self.assertEqual(req.approved_by, "rochak")

    def test_blueprint_is_metadata_only(self):
        # no callable / code field on the model
        b = SkillBlueprint(id="x", recommendation_id="r0")
        for value in b.model_dump().values():
            self.assertNotIn("code", str(type(value)).lower())
        self.assertFalse(any(callable(v) for v in b.model_dump().values()))


class TestInterface(unittest.TestCase):
    def test_contract_single_method(self):
        self.assertTrue(hasattr(ISkillCreator, "create_blueprint"))
        # abstract — cannot instantiate directly
        with self.assertRaises(TypeError):
            ISkillCreator()

    def test_no_installer_generator_validator_methods(self):
        for banned in ["install", "generate_code", "validate", "execute", "run", "load"]:
            self.assertFalse(hasattr(ISkillCreator, banned), f"unexpected method: {banned}")


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
            "brain.evolution.models",
            "brain.skill_creator.models",
            "brain.skill_creator.interfaces",
            "brain.skill_creator.blueprint_builder",
            "brain.skill_creator.blueprint_verifier",
            "brain.skill_creator.blueprint_generator",
            "brain.skill_creator.blueprint_tester",
            "brain.skill_creator.blueprint_approver",
            "brain.skill_creator.blueprint_installer",
            "brain.skill_creator.blueprint_registry",
            "brain.skill_creator.lifecycle_manager",
            "brain.skill_creator.marketplace_publisher",
            "brain.skill_creator.rollback_manager",
            "pydantic", "typing", "abc", "__future__",
        )
        for rel in ["brain/skill_creator/models.py",
                    "brain/skill_creator/interfaces.py",
                    "brain/skill_creator/__init__.py"]:
            for m in self._imports(rel):
                self.assertTrue(m.startswith(allowed), f"{rel}: forbidden import {m}")

    def test_no_runtime_imports(self):
        for rel in ["brain/skill_creator/models.py", "brain/skill_creator/interfaces.py"]:
            modules = self._imports(rel)
            for banned in [
                "brain.core.brain_core", "brain.planning.rule_planner",
                "brain.planning.llm_planner", "brain.workspace.memory",
                "brain.reflection.engine", "brain.skills.registry",
                "core.runtime_facade", "core.bootstrap", "server",
            ]:
                self.assertNotIn(banned, modules, f"{rel} must not import {banned}")

    def test_no_executable_payload_in_package(self):
        # foundation package must be contracts only — no os/subprocess/exec/eval/compile
        for rel in ["brain/skill_creator/models.py", "brain/skill_creator/interfaces.py"]:
            src = (backend_dir / rel).read_text(encoding="utf-8")
            for banned in ["subprocess", "os.system", "exec(", "eval(", "compile(", "__import__"]:
                self.assertNotIn(banned, src, f"{rel} must contain no executable payload: {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        # Registered (contract present). Concrete provider arrives in 7.2;
        # it remains dormant (no runtime path consumes it).
        self.assertTrue(c.is_registered(ISkillCreator))


if __name__ == "__main__":
    unittest.main()
