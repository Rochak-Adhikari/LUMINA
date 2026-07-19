"""
tests/test_phase_5_5_step5.py — Phase 5.5 Step 5: Plugin-ready Registry

Skills carry a SOURCE (builtin/plugin/mcp/generated/remote). The registry
accepts multiple sources; the planner receives identical SkillMetadata
regardless of source; the resolver stays source-agnostic (no source
preference).

Proves: default source, explicit sources, mixed-source registry, source-
filtered search, source-agnostic resolver, backward-compatible register(),
planner/manager unaffected.
"""

import asyncio
import unittest
from unittest.mock import MagicMock
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

sys.modules.setdefault('google', MagicMock())
sys.modules.setdefault('google.genai', MagicMock())
sys.modules.setdefault('google.genai.types', MagicMock())

from brain.skills.models import SkillSpec
from brain.skills.metadata import SkillMetadata
from brain.skills.registry import SkillRegistry
from brain.skills.resolver import CapabilityResolver
from brain.skills import sources
from brain.skills.manager import SkillManager
from brain.skills.executors.legacy_tool_executor import LegacyToolExecutor
from brain.core.models import Task


def _spec(id, name="S", tags=(), permissions=()):
    return SkillSpec(id=id, name=name, tags=list(tags),
                     permissions=list(permissions), provider="legacy",
                     provider_ref=id.split(".")[-1])


class TestSourceAssignment(unittest.TestCase):
    def test_default_source_builtin(self):
        reg = SkillRegistry()
        reg.register(_spec("a.b"))                      # no source arg
        self.assertEqual(reg.get_metadata("a.b").source, "builtin")

    def test_explicit_builtin(self):
        reg = SkillRegistry()
        reg.register(_spec("a.b"), source=sources.BUILTIN)
        self.assertEqual(reg.get_metadata("a.b").source, "builtin")

    def test_plugin_source(self):
        reg = SkillRegistry()
        reg.register(_spec("p.x"), source=sources.PLUGIN)
        self.assertEqual(reg.get_metadata("p.x").source, "plugin")

    def test_mcp_source(self):
        reg = SkillRegistry()
        reg.register(_spec("m.x"), source=sources.MCP)
        self.assertEqual(reg.get_metadata("m.x").source, "mcp")

    def test_generated_source(self):
        reg = SkillRegistry()
        reg.register(_spec("g.x"), source=sources.GENERATED)
        self.assertEqual(reg.get_metadata("g.x").source, "generated")


class TestMixedSourceRegistry(unittest.TestCase):
    def setUp(self):
        self.reg = SkillRegistry()
        self.reg.register(_spec("b.one", tags=["util"]), source=sources.BUILTIN)
        self.reg.register(_spec("p.two", tags=["util"]), source=sources.PLUGIN)
        self.reg.register(_spec("m.three", tags=["util"]), source=sources.MCP)

    def test_all_registered(self):
        self.assertEqual(len(self.reg), 3)
        self.assertEqual(len(self.reg.all_metadata()), 3)

    def test_search_across_all_sources_by_default(self):
        # source=None → every source returned.
        got = {m.id for m in self.reg.search(tags=["util"])}
        self.assertEqual(got, {"b.one", "p.two", "m.three"})

    def test_search_filtered_by_source(self):
        self.assertEqual([m.id for m in self.reg.search(source=sources.PLUGIN)],
                         ["p.two"])
        self.assertEqual([m.id for m in self.reg.search(source=sources.MCP)],
                         ["m.three"])

    def test_search_preserves_registration_order(self):
        got = [m.id for m in self.reg.search(tags=["util"])]
        self.assertEqual(got, ["b.one", "p.two", "m.three"])


class TestResolverSourceAgnostic(unittest.TestCase):
    def test_resolver_ignores_source_for_scoring(self):
        # Two identical-scoring skills, different sources; tie → first
        # registered wins REGARDLESS of source (no source preference).
        reg = SkillRegistry()
        reg.register(_spec("first.nav", tags=["navigation"]), source=sources.PLUGIN)
        reg.register(_spec("second.nav", tags=["navigation"]), source=sources.BUILTIN)
        best = CapabilityResolver(reg).resolve(category="navigation")
        self.assertEqual(best.id, "first.nav")  # registration order, not source

    def test_resolver_score_independent_of_source(self):
        reg = SkillRegistry()
        r = CapabilityResolver(reg)
        a = SkillMetadata.from_spec(_spec("a", tags=["navigation"]), source="plugin")
        b = SkillMetadata.from_spec(_spec("b", tags=["navigation"]), source="mcp")
        self.assertEqual(r.score(a, category="navigation"),
                         r.score(b, category="navigation"))


class TestBackwardCompatAndNoRegression(unittest.TestCase):
    def test_register_without_source_unchanged(self):
        reg = SkillRegistry()
        spec = _spec("x.y", tags=["t"])
        reg.register(spec)                              # legacy call shape
        self.assertIs(reg.get("x.y"), spec)
        self.assertEqual(len(reg), 1)

    def test_duplicate_still_rejected_with_source(self):
        reg = SkillRegistry()
        reg.register(_spec("x.y"), source=sources.PLUGIN)
        with self.assertRaises(ValueError):
            reg.register(_spec("x.y"), source=sources.MCP)

    def test_manager_execution_unaffected_by_source(self):
        # SkillManager still executes by skill_id regardless of source.
        reg = SkillRegistry()
        reg.register(_spec("p.run"), source=sources.PLUGIN)
        async def dispatch(ref, params):
            return {"ran": ref}
        mgr = SkillManager(reg, [LegacyToolExecutor(dispatch=dispatch)])
        result = asyncio.run(mgr.execute(Task(intent="t", skill_id="p.run")))
        self.assertTrue(result.ok)

    def test_metadata_has_source_field(self):
        fields = {f for f in SkillMetadata.__dataclass_fields__}
        self.assertIn("source", fields)


if __name__ == '__main__':
    unittest.main()
