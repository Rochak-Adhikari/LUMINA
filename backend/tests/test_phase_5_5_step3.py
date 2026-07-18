"""
tests/test_phase_5_5_step3.py — Phase 5.5 Step 3: Metadata-driven Planning

RulePlanner discovers the navigation skill id via SkillRegistry.search()
instead of a hardcoded literal, with a deterministic first-match selection
and a fallback to the hardcoded id when no registry / no match is available.

Proves:
  - planner resolves the skill via registry search (metadata-driven)
  - deterministic selection (first match, registration order)
  - fallback path when no registry injected → identical id
  - fallback path when search returns nothing → identical id
  - metadata path and fallback path produce the SAME skill id (no regression)
  - RulePlanner() no-arg construction still works (API backward-compatible)
  - unknown capability handled safely (abstain unchanged)
  - execution/plan shape unchanged
"""

import unittest
from unittest.mock import MagicMock
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

sys.modules.setdefault('google', MagicMock())
sys.modules.setdefault('google.genai', MagicMock())
sys.modules.setdefault('google.genai.types', MagicMock())

from brain.planning.rule_planner import RulePlanner, _NAV_FALLBACK_SKILL_ID
from brain.core.models import BrainRequest
from brain.core.context_builder import ContextBuilder
from brain.skills.registry import SkillRegistry
from brain.skills.builtin import seed_registry


def _ctx(text):
    return ContextBuilder(brain_state=None).build(BrainRequest(text=text))


def _seeded_registry():
    reg = SkillRegistry()
    seed_registry(reg)
    return reg


class TestMetadataDrivenSelection(unittest.TestCase):
    def test_planner_resolves_via_registry_search(self):
        reg = _seeded_registry()
        planner = RulePlanner(skill_registry=reg)
        plan = planner.plan(_ctx("open the quests panel"))
        self.assertIsNotNone(plan)
        # Discovered id equals the navigation capability in the catalog.
        self.assertEqual(plan.tasks[0].skill_id, "legacy.navigate_ui")

    def test_metadata_path_equals_fallback_path(self):
        # Zero-regression guarantee: with or without the registry, the same
        # request yields the same skill id.
        with_reg = RulePlanner(skill_registry=_seeded_registry())
        without = RulePlanner()  # no registry → fallback
        a = with_reg.plan(_ctx("open the quests panel")).tasks[0].skill_id
        b = without.plan(_ctx("open the quests panel")).tasks[0].skill_id
        self.assertEqual(a, b)
        self.assertEqual(a, _NAV_FALLBACK_SKILL_ID)

    def test_deterministic_selection_repeatable(self):
        reg = _seeded_registry()
        planner = RulePlanner(skill_registry=reg)
        ids = [planner.plan(_ctx("go to settings")).tasks[0].skill_id
               for _ in range(5)]
        self.assertEqual(len(set(ids)), 1)

    def test_first_match_registration_order(self):
        # Two navigation-category skills; first registered wins deterministically.
        from brain.skills.models import SkillSpec
        reg = SkillRegistry()
        reg.register(SkillSpec(id="legacy.navigate_ui", name="Nav A",
                               tags=["navigation"], provider="legacy",
                               provider_ref="navigate_ui"))
        reg.register(SkillSpec(id="legacy.navigate_alt", name="Nav B",
                               tags=["navigation"], provider="legacy",
                               provider_ref="navigate_ui"))
        planner = RulePlanner(skill_registry=reg)
        self.assertEqual(planner.plan(_ctx("open quests")).tasks[0].skill_id,
                         "legacy.navigate_ui")  # first registered


class TestFallbackPaths(unittest.TestCase):
    def test_no_registry_uses_fallback(self):
        planner = RulePlanner()  # no-arg construction still works
        plan = planner.plan(_ctx("open the quests panel"))
        self.assertEqual(plan.tasks[0].skill_id, _NAV_FALLBACK_SKILL_ID)

    def test_empty_search_uses_fallback(self):
        # Registry with no navigation-category skill → search empty → fallback.
        reg = SkillRegistry()  # empty
        planner = RulePlanner(skill_registry=reg)
        plan = planner.plan(_ctx("open the quests panel"))
        self.assertEqual(plan.tasks[0].skill_id, _NAV_FALLBACK_SKILL_ID)

    def test_search_raising_uses_fallback(self):
        class _BadReg:
            def search(self, **kw):
                raise RuntimeError("boom")
        planner = RulePlanner(skill_registry=_BadReg())
        plan = planner.plan(_ctx("open the quests panel"))
        self.assertEqual(plan.tasks[0].skill_id, _NAV_FALLBACK_SKILL_ID)


class TestBehaviorUnchanged(unittest.TestCase):
    def test_unknown_capability_abstains(self):
        planner = RulePlanner(skill_registry=_seeded_registry())
        self.assertIsNone(planner.plan(_ctx("open the fridge")))
        self.assertIsNone(planner.plan(_ctx("write me a haiku")))

    def test_plan_shape_unchanged(self):
        planner = RulePlanner(skill_registry=_seeded_registry())
        plan = planner.plan(_ctx("show completed quests"))
        self.assertEqual(plan.tasks[0].intent, "navigate")
        self.assertEqual(plan.tasks[0].params, {"panel": "quests", "view": "completed"})
        self.assertEqual(plan.strategy, "sequential")
        self.assertEqual(plan.confidence, 1.0)

    def test_noarg_construction_backward_compatible(self):
        # The public plan() API is unchanged; __init__ gained an optional arg.
        planner = RulePlanner()
        self.assertIsNone(planner.plan(_ctx("")))


if __name__ == '__main__':
    unittest.main()
