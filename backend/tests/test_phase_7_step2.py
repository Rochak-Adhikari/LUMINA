"""
tests/test_phase_7_step2.py — Milestone 7.2 Verification (Blueprint Builder)

Verifies the deterministic EvolutionRecommendationSet → SkillBlueprintSet
transformer:

  - deterministic mapping (improve_strategy/merge_memory/future_skill_candidate
    → blueprint; observe_more/keep_strategy → none)
  - deterministic ids (bp:<kind>:<target>)
  - frozen, serializable blueprints; metadata only
  - provenance present; recommendation_id present (audit trail)
  - package_layout frozen; capability declarations present
  - approval_required always True; lifecycle starts at "draft"
  - byte-identical repeated execution; input unchanged
  - no forbidden imports; no subprocess/exec/eval/compile; no runtime mutation
  - BlueprintBuilder registered dormant

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
from brain.skill_creator.models import SkillBlueprint, SkillBlueprintSet
from brain.skill_creator.blueprint_builder import BlueprintBuilder
from brain.skill_creator.interfaces import ISkillCreator


def _rec(id, kind, target="", related=None, confidence=0.5, reason="because"):
    return EvolutionRecommendation(
        id=id, kind=kind, target=target, reason=reason,
        confidence=confidence, related_ids=list(related or []),
    )


def _set(*recs):
    return EvolutionRecommendationSet(
        recommendations=list(recs), recommendation_count=len(recs)
    )


class TestMapping(unittest.TestCase):
    def setUp(self):
        self.b = BlueprintBuilder()

    def test_is_interface(self):
        self.assertIsInstance(self.b, ISkillCreator)

    def test_improve_strategy_maps(self):
        s = self.b.create_blueprint(_set(_rec("r1", "improve_strategy", "seq")))
        self.assertEqual(s.blueprint_count, 1)
        self.assertEqual(s.blueprints[0].skill_kind, "strategy_optimizer")

    def test_merge_memory_maps(self):
        s = self.b.create_blueprint(_set(_rec("r1", "merge_memory", "dupes")))
        self.assertEqual(s.blueprints[0].skill_kind, "memory_consolidation")

    def test_future_skill_candidate_maps(self):
        s = self.b.create_blueprint(_set(_rec("r1", "future_skill_candidate", "web")))
        self.assertEqual(s.blueprints[0].skill_kind, "new_skill")

    def test_observe_more_produces_none(self):
        s = self.b.create_blueprint(_set(_rec("r1", "observe_more")))
        self.assertEqual(s.blueprint_count, 0)

    def test_keep_strategy_produces_none(self):
        s = self.b.create_blueprint(_set(_rec("r1", "keep_strategy", "seq")))
        self.assertEqual(s.blueprint_count, 0)

    def test_mixed_set(self):
        s = self.b.create_blueprint(_set(
            _rec("r1", "improve_strategy", "seq"),
            _rec("r2", "keep_strategy", "dag"),
            _rec("r3", "merge_memory", "n"),
        ))
        self.assertEqual(s.blueprint_count, 2)
        self.assertEqual([b.recommendation_id for b in s.blueprints], ["r1", "r3"])


class TestBlueprintContent(unittest.TestCase):
    def setUp(self):
        self.b = BlueprintBuilder()
        self.bp = self.b.create_blueprint(
            _set(_rec("r1", "improve_strategy", "seq", related=["seq"]))
        ).blueprints[0]

    def test_deterministic_id(self):
        self.assertEqual(self.bp.id, "bp:strategy_optimizer:seq")

    def test_recommendation_id_present(self):
        self.assertEqual(self.bp.recommendation_id, "r1")

    def test_provenance_present(self):
        p = self.bp.provenance
        self.assertEqual(p["recommendation_id"], "r1")
        self.assertEqual(p["phase"], "7.2")
        self.assertEqual(p["generated_by"], "BlueprintBuilder")
        self.assertEqual(p["schema_version"], "1.0")

    def test_schema_version(self):
        self.assertEqual(self.bp.blueprint_schema_version, "1.0")

    def test_package_layout_frozen(self):
        self.assertEqual(self.bp.package_layout, {
            "manifest": "manifest.json",
            "implementation": "skill.py",
            "tests": "tests.py",
            "metadata": "metadata.json",
            "readme": "README.md",
            "provenance": "provenance.json",
        })

    def test_capability_declarations(self):
        self.assertEqual(self.bp.provided_capabilities, ["strategy_optimizer"])
        self.assertEqual(self.bp.required_capabilities, ["seq"])

    def test_approval_required_true(self):
        self.assertTrue(self.bp.approval_required)

    def test_lifecycle_draft(self):
        self.assertEqual(self.bp.status, "draft")

    def test_estimate_defaults(self):
        self.assertEqual(self.bp.estimated_tokens, 0)
        self.assertEqual(self.bp.estimated_files, 0)
        self.assertEqual(self.bp.estimated_test_count, 0)

    def test_rollback_strategy(self):
        self.assertEqual(self.bp.rollback_strategy, "remove_generated_skill")

    def test_human_summary_deterministic(self):
        self.assertIn("strategy_optimizer", self.bp.human_summary)
        self.assertIn("seq", self.bp.human_summary)

    def test_frozen(self):
        with self.assertRaises(Exception):
            self.bp.status = "active"

    def test_serializable(self):
        import json
        json.dumps(self.bp.model_dump())


class TestDeterminism(unittest.TestCase):
    def test_byte_identical_repeat(self):
        b = BlueprintBuilder()
        s = _set(_rec("r1", "improve_strategy", "seq"), _rec("r2", "merge_memory", "n"))
        self.assertEqual(b.create_blueprint(s).model_dump(), b.create_blueprint(s).model_dump())

    def test_input_unchanged(self):
        b = BlueprintBuilder()
        s = _set(_rec("r1", "improve_strategy", "seq"))
        before = s.model_dump()
        b.create_blueprint(s)
        self.assertEqual(s.model_dump(), before)

    def test_empty_input(self):
        s = BlueprintBuilder().create_blueprint(_set())
        self.assertEqual(s.blueprint_count, 0)


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
            "pydantic", "typing", "abc", "__future__",
        )
        for m in self._imports("brain/skill_creator/blueprint_builder.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_forbidden_runtime_imports(self):
        modules = self._imports("brain/skill_creator/blueprint_builder.py")
        for banned in [
            "brain.core.brain_core", "core.runtime_facade", "brain.workspace.memory",
            "brain.planning.rule_planner", "brain.planning.llm_planner",
            "brain.reflection.engine", "brain.evolution.recommender",
            "brain.skills.registry", "core.bootstrap", "server", "subprocess",
        ]:
            self.assertNotIn(banned, modules, f"builder must not import {banned}")

    def test_no_executable_payload(self):
        src = (backend_dir / "brain/skill_creator/blueprint_builder.py").read_text(encoding="utf-8")
        for banned in ["subprocess", "os.system", "exec(", "eval(", "compile(", "__import__", "open("]:
            self.assertNotIn(banned, src, f"builder must contain no executable payload: {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(ISkillCreator))
        # Resolvable now, but dormant — empty input yields empty set, no side effects.
        out = c.resolve(ISkillCreator).create_blueprint(_set())
        self.assertEqual(out.blueprint_count, 0)


if __name__ == "__main__":
    unittest.main()
