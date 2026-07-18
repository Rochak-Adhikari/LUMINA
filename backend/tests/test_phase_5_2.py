"""
tests/test_phase_5_2.py — Milestone 5.2 Verification
(RulePlanner + SkillRegistry + SkillManager + LegacyToolExecutor)

Verifies:
  - planner / registry / manager resolve from DI (singletons)
  - RuntimeFacade exposes all three
  - registry register / get / find / all
  - builtin seed present
  - RulePlanner deterministic matches + None for unknown
  - manager resolves executor and returns SkillResult for every failure mode
  - unbound legacy executor is inert (ok=False, never raises)
  - BrainCore.handle() still pass-through (handled=False) — no routing
  - server.py has no Phase 5 references
  - no circular imports

Stdlib unittest; heavy deps mocked (pattern from test_phase_4_4/5_1).
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

from core.container import DependencyContainer
from core.bootstrap import Bootstrapper
from core.runtime_facade import RuntimeFacade
from brain.core.interfaces import IPlanner, IBrainCore
from brain.core.models import BrainRequest, BrainResult, Plan, Task
from brain.core.context_builder import ContextBuilder
from brain.planning.rule_planner import RulePlanner
from brain.skills.models import SkillSpec, SkillResult
from brain.skills.registry import SkillRegistry
from brain.skills.manager import SkillManager
from brain.skills.executors.legacy_tool_executor import LegacyToolExecutor
from brain.skills.builtin import BUILTIN_SKILLS


def _bootstrapped():
    container = DependencyContainer()
    bootstrapper = Bootstrapper(container=container, kasa_agent=None)
    bootstrapper.bootstrap()
    return container, bootstrapper


def _ctx(text):
    """BrainContext for plain text (no BrainState needed)."""
    return ContextBuilder(brain_state=None).build(BrainRequest(text=text))


class TestPhase5_2_DI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container, cls.bootstrapper = _bootstrapped()
        cls.facade = RuntimeFacade(cls.container)

    def test_planner_resolves(self):
        p1 = self.container.resolve(IPlanner)
        self.assertIsInstance(p1, RulePlanner)
        self.assertIs(p1, self.container.resolve(IPlanner))

    def test_registry_resolves(self):
        r1 = self.container.resolve(SkillRegistry)
        self.assertIsInstance(r1, SkillRegistry)
        self.assertIs(r1, self.container.resolve(SkillRegistry))

    def test_manager_resolves(self):
        m1 = self.container.resolve(SkillManager)
        self.assertIsInstance(m1, SkillManager)
        self.assertIs(m1, self.container.resolve(SkillManager))

    def test_runtime_facade_exposes_all(self):
        self.assertIs(self.facade.planner, self.container.resolve(IPlanner))
        self.assertIs(self.facade.skill_registry, self.container.resolve(SkillRegistry))
        self.assertIs(self.facade.skill_manager, self.container.resolve(SkillManager))

    def test_registry_seeded_with_builtins(self):
        registry = self.facade.skill_registry
        self.assertEqual(len(registry), len(BUILTIN_SKILLS))
        for spec in BUILTIN_SKILLS:
            self.assertIsNotNone(registry.get(spec.id))


class TestPhase5_2_Registry(unittest.TestCase):
    def setUp(self):
        self.registry = SkillRegistry()
        self.spec = SkillSpec(
            id="test.echo", name="Echo", description="Echo a value back.",
            tags=["test", "echo"], provider="legacy", provider_ref="echo",
        )

    def test_register_and_get(self):
        self.registry.register(self.spec)
        self.assertIs(self.registry.get("test.echo"), self.spec)
        self.assertIsNone(self.registry.get("missing"))

    def test_duplicate_registration_raises(self):
        self.registry.register(self.spec)
        with self.assertRaises(ValueError):
            self.registry.register(self.spec)

    def test_find_by_query_and_tags(self):
        self.registry.register(self.spec)
        self.registry.register(SkillSpec(
            id="test.other", name="Other", description="Unrelated.",
            tags=["test"], provider="legacy",
        ))
        self.assertEqual([s.id for s in self.registry.find(query="echo")], ["test.echo"])
        self.assertEqual([s.id for s in self.registry.find(tags=["echo"])], ["test.echo"])
        self.assertEqual(len(self.registry.find(tags=["test"])), 2)
        self.assertEqual(len(self.registry.find()), 2)
        self.assertEqual(len(self.registry.all()), 2)


class TestPhase5_2_RulePlanner(unittest.TestCase):
    def setUp(self):
        self.planner = RulePlanner()

    def test_navigation_intent(self):
        plan = self.planner.plan(_ctx("open the quests panel"))
        self.assertIsInstance(plan, Plan)
        self.assertEqual(len(plan.tasks), 1)
        self.assertEqual(plan.tasks[0].skill_id, "legacy.navigate_ui")
        self.assertEqual(plan.tasks[0].intent, "navigate")
        self.assertEqual(plan.tasks[0].params.get("panel"), "quests")
        self.assertEqual(plan.tasks[0].params.get("view"), "all")

    def test_memory_verbs_not_planned(self):
        # Phase 5.4 Step 1: no dispatchable memory tool exists; memory verbs
        # are handled by the legacy inline path, not planned here.
        self.assertIsNone(self.planner.plan(_ctx("remember that I prefer dark mode")))
        self.assertIsNone(self.planner.plan(_ctx("forget about my old address")))
        self.assertIsNone(self.planner.plan(_ctx("what do you remember about me?")))

    def test_unknown_panel_returns_none(self):
        # Navigation target that maps to no real panel → abstain.
        self.assertIsNone(self.planner.plan(_ctx("open the fridge")))

    def test_unknown_returns_none(self):
        self.assertIsNone(self.planner.plan(_ctx("write me a haiku about rain")))
        self.assertIsNone(self.planner.plan(_ctx("")))

    def test_voice_tool_requests_not_planned(self):
        ctx = ContextBuilder(brain_state=None).build(
            BrainRequest(channel="voice_tool", text="open settings",
                         tool_call={"name": "navigate"})
        )
        self.assertIsNone(self.planner.plan(ctx))

    def test_deterministic(self):
        a = self.planner.plan(_ctx("open settings"))
        b = self.planner.plan(_ctx("open settings"))
        self.assertEqual(a.tasks[0].params, b.tasks[0].params)
        self.assertEqual(a.tasks[0].intent, b.tasks[0].intent)


class TestPhase5_2_Manager(unittest.TestCase):
    def setUp(self):
        self.registry = SkillRegistry()
        self.spec = SkillSpec(id="test.legacy", name="T", provider="legacy",
                              provider_ref="t_ref")
        self.registry.register(self.spec)

    def test_resolve_executor(self):
        ex = LegacyToolExecutor()
        manager = SkillManager(self.registry, [ex])
        self.assertIs(manager.resolve_executor(self.spec), ex)
        other = SkillSpec(id="x", name="X", provider="mcp")
        self.assertIsNone(manager.resolve_executor(other))

    def test_execute_with_bound_dispatch(self):
        calls = []
        def dispatch(ref, params):
            calls.append((ref, params))
            return {"echoed": params}
        manager = SkillManager(self.registry, [LegacyToolExecutor(dispatch=dispatch)])
        result = asyncio.run(manager.execute(Task(intent="t", skill_id="test.legacy",
                                                  params={"a": 1})))
        self.assertIsInstance(result, SkillResult)
        self.assertTrue(result.ok)
        self.assertEqual(calls, [("t_ref", {"a": 1})])
        self.assertEqual(result.output, {"echoed": {"a": 1}})

    def test_execute_with_async_dispatch(self):
        async def dispatch(ref, params):
            return "async-ok"
        manager = SkillManager(self.registry, [LegacyToolExecutor(dispatch=dispatch)])
        result = asyncio.run(manager.execute(Task(intent="t", skill_id="test.legacy")))
        self.assertTrue(result.ok)
        self.assertEqual(result.output, "async-ok")

    def test_unbound_executor_is_inert(self):
        manager = SkillManager(self.registry, [LegacyToolExecutor(dispatch=None)])
        result = asyncio.run(manager.execute(Task(intent="t", skill_id="test.legacy")))
        self.assertFalse(result.ok)
        self.assertIn("no dispatch bound", result.error)

    def test_failure_modes_never_raise(self):
        manager = SkillManager(self.registry, [LegacyToolExecutor()])
        r1 = asyncio.run(manager.execute(Task(intent="t")))          # no skill_id
        r2 = asyncio.run(manager.execute(Task(intent="t", skill_id="ghost")))  # unknown
        self.assertFalse(r1.ok)
        self.assertFalse(r2.ok)

        def bad_dispatch(ref, params):
            raise RuntimeError("boom")
        manager2 = SkillManager(self.registry, [LegacyToolExecutor(dispatch=bad_dispatch)])
        r3 = asyncio.run(manager2.execute(Task(intent="t", skill_id="test.legacy")))
        self.assertFalse(r3.ok)
        self.assertIn("boom", r3.error)


class TestPhase5_2_No_Runtime_Change(unittest.TestCase):
    """Guards: runtime identical, no wiring, no server references."""

    @classmethod
    def setUpClass(cls):
        cls.container, cls.bootstrapper = _bootstrapped()

    def test_brain_core_still_pass_through(self):
        core = self.container.resolve(IBrainCore)
        # A request RulePlanner WOULD match must still not be planned/executed
        result = asyncio.run(core.handle(BrainRequest(text="open the settings panel")))
        self.assertIsInstance(result, BrainResult)
        self.assertFalse(result.handled)
        self.assertIsNone(result.plan)

    def test_server_has_no_phase5_references(self):
        source = (backend_dir / "server.py").read_text(encoding='utf-8')
        for token in ("RulePlanner", "SkillRegistry", "SkillManager",
                      "brain.planning", "brain.skills", "BrainCore"):
            self.assertNotIn(token, source,
                             f"server.py must not reference {token} in Phase 5.2")

    def test_di_registration_count(self):
        """Exactly the expected Phase 5.1 + 5.2 brain-stack keys registered."""
        from brain.core.interfaces import IContextBuilder
        for key in (IPlanner, IBrainCore, IContextBuilder, SkillRegistry, SkillManager):
            self.assertTrue(self.container.is_registered(key),
                            f"{key} must be registered")
        # Metadata registry unchanged (no new records in 5.2)
        from core.metadata import ServiceMetadataRegistry
        registry = self.container.resolve(ServiceMetadataRegistry)
        self.assertEqual(len(registry), 11,
                         "ServiceMetadataRegistry must stay at 11 records")

    def test_no_circular_imports(self):
        import importlib
        import brain.planning
        import brain.skills
        importlib.reload(brain.planning)
        importlib.reload(brain.skills)


if __name__ == '__main__':
    unittest.main()
