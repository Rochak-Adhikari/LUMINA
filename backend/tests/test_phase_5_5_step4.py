"""
tests/test_phase_5_5_step4.py — Phase 5.5 Step 4: Capability Ranking

CapabilityResolver: deterministic ranking between SkillRegistry discovery and
Task.skill_id selection. Proves scoring, tie-break (registration order),
determinism, empty handling, and zero planner/runtime regression.
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

from brain.skills.metadata import SkillMetadata
from brain.skills.registry import SkillRegistry
from brain.skills.resolver import CapabilityResolver
from brain.skills.models import SkillSpec
from brain.planning.rule_planner import RulePlanner, _NAV_FALLBACK_SKILL_ID
from brain.core.models import BrainRequest
from brain.core.context_builder import ContextBuilder
from brain.skills.builtin import seed_registry


def _md(id, category="general", permissions=(), tags=(), inputs=(), outputs=(),
        confirmation=False):
    return SkillMetadata(id=id, display_name=id, category=category,
                         permissions=tuple(permissions), tags=tuple(tags),
                         inputs=tuple(inputs), outputs=tuple(outputs),
                         confirmation_required=confirmation)


class _MDRegistry(SkillRegistry):
    """Register SkillMetadata directly (inputs/outputs/confirmation are empty
    via from_spec, so tests inject metadata to exercise ranking)."""
    def add(self, md):
        self._metadata[md.id] = md
        self._specs[md.id] = SkillSpec(id=md.id, name=md.display_name, provider="legacy")
        return self


def _ctx(text):
    return ContextBuilder(brain_state=None).build(BrainRequest(text=text))


class TestScoring(unittest.TestCase):
    def setUp(self):
        self.r = CapabilityResolver(_MDRegistry())

    def test_category_match(self):
        self.assertEqual(self.r.score(_md("a", category="browser"), category="browser"), 50)
        self.assertEqual(self.r.score(_md("a", category="x"), category="browser"), 0)

    def test_permission_match(self):
        self.assertEqual(self.r.score(_md("a", permissions=["internet"]),
                                      permission="internet"), 20)

    def test_tag_match_each(self):
        self.assertEqual(self.r.score(_md("a", tags=["s", "t"]), tags=["s", "t"]), 20)
        self.assertEqual(self.r.score(_md("a", tags=["s"]), tags=["s", "t"]), 10)

    def test_input_output_match_each(self):
        self.assertEqual(self.r.score(_md("a", inputs=["url", "q"]), inputs=["url", "q"]), 10)
        self.assertEqual(self.r.score(_md("a", outputs=["page"]), outputs=["page"]), 5)

    def test_confirmation_match(self):
        self.assertEqual(self.r.score(_md("a", confirmation=True),
                                      confirmation_required=True), 5)
        self.assertEqual(self.r.score(_md("a", confirmation=False),
                                      confirmation_required=True), 0)

    def test_combined_score(self):
        md = _md("a", category="browser", permissions=["internet"],
                 tags=["search"], inputs=["url"], outputs=["page"], confirmation=True)
        s = self.r.score(md, category="browser", permission="internet",
                         tags=["search"], inputs=["url"], outputs=["page"],
                         confirmation_required=True)
        self.assertEqual(s, 50 + 20 + 10 + 5 + 5 + 5)


class TestRankAndResolve(unittest.TestCase):
    def _reg(self, *mds):
        reg = _MDRegistry()
        for m in mds:
            reg.add(m)
        return reg

    def test_single_candidate(self):
        reg = self._reg(_md("only", category="browser"))
        best = CapabilityResolver(reg).resolve(category="browser")
        self.assertEqual(best.id, "only")

    def test_multiple_highest_wins(self):
        reg = self._reg(
            _md("weak", category="browser"),                       # +50
            _md("strong", category="browser", permissions=["internet"]),  # +70
        )
        best = CapabilityResolver(reg).resolve(category="browser", permission="internet")
        self.assertEqual(best.id, "strong")

    def test_tie_first_registered_wins(self):
        reg = self._reg(
            _md("first", category="browser"),
            _md("second", category="browser"),
        )
        best = CapabilityResolver(reg).resolve(category="browser")
        self.assertEqual(best.id, "first")  # equal score → earlier registered

    def test_category_ranking(self):
        reg = self._reg(_md("a", category="x"), _md("b", category="browser"))
        self.assertEqual(CapabilityResolver(reg).resolve(category="browser").id, "b")

    def test_permission_ranking(self):
        reg = self._reg(_md("a", category="c"),
                        _md("b", category="c", permissions=["internet"]))
        self.assertEqual(
            CapabilityResolver(reg).resolve(category="c", permission="internet").id, "b")

    def test_tag_ranking(self):
        reg = self._reg(_md("a", category="c", tags=["x"]),
                        _md("b", category="c", tags=["x", "y"]))
        self.assertEqual(
            CapabilityResolver(reg).resolve(category="c", tags=["x", "y"]).id, "b")

    def test_input_output_ranking(self):
        reg = self._reg(_md("a", category="c", inputs=["url"]),
                        _md("b", category="c", inputs=["url", "q"]))
        self.assertEqual(
            CapabilityResolver(reg).resolve(category="c", inputs=["url", "q"]).id, "b")

    def test_empty_registry_returns_none(self):
        self.assertIsNone(CapabilityResolver(_MDRegistry()).resolve(category="x"))

    def test_no_match_returns_none(self):
        reg = self._reg(_md("a", category="x"))
        self.assertIsNone(CapabilityResolver(reg).resolve(category="browser"))

    def test_deterministic_stable_across_runs(self):
        reg = self._reg(
            _md("a", category="c", permissions=["p"]),
            _md("b", category="c", permissions=["p"]),
            _md("c", category="c", permissions=["p"]),
        )
        r = CapabilityResolver(reg)
        winners = {r.resolve(category="c", permission="p").id for _ in range(5)}
        self.assertEqual(winners, {"a"})  # deterministic, tie → first


class TestPlannerIntegration(unittest.TestCase):
    def _seeded(self):
        reg = SkillRegistry()
        seed_registry(reg)
        return reg

    def test_planner_uses_resolver(self):
        planner = RulePlanner(skill_registry=self._seeded())
        plan = planner.plan(_ctx("open the quests panel"))
        self.assertEqual(plan.tasks[0].skill_id, "legacy.navigate_ui")

    def test_planner_no_regression_vs_fallback(self):
        a = RulePlanner(skill_registry=self._seeded()).plan(
            _ctx("go to settings")).tasks[0].skill_id
        b = RulePlanner().plan(_ctx("go to settings")).tasks[0].skill_id
        self.assertEqual(a, b)
        self.assertEqual(a, _NAV_FALLBACK_SKILL_ID)

    def test_planner_no_ranking_logic(self):
        # No scoring constants / rank logic in the planner module.
        src = (backend_dir / "brain" / "planning" / "rule_planner.py").read_text(
            encoding='utf-8')
        for token in ("+50", "+20", "def score", "def rank", "sort("):
            self.assertNotIn(token, src, f"ranking logic leaked into planner: {token}")


if __name__ == '__main__':
    unittest.main()
