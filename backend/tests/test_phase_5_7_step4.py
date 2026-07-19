"""
tests/test_phase_5_7_step4.py — Phase 5.7.4: BrainCore Reflection integration

Reflection produced once per completed request, attached to
BrainResult.reflection. Read-only; failure never fails the request; handling
semantics unchanged.
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
from brain.core.brain_core import BrainCore
from brain.core.context_builder import ContextBuilder
from brain.core.models import BrainRequest, BrainResult, Reflection, Plan, Task
from brain.core.interfaces import IBrainCore
from brain.reflection.engine import ReflectionEngine
from brain.skills.models import SkillResult


class _StubPlanner:
    def __init__(self, plan): self._p = plan
    def plan(self, ctx): return self._p


class _StubManager:
    def __init__(self, results): self._r = list(results); self.calls = 0
    async def execute(self, task):
        r = self._r[self.calls]; self.calls += 1; return r


class _CountingEngine:
    def __init__(self): self.calls = 0
    def reflect(self, request, plan, results, context):
        self.calls += 1
        return Reflection(request_id=request.request_id, success=all(getattr(x,"ok",False) for x in results))


def _cb():
    return ContextBuilder(brain_state=None)


class TestReflectionAttached(unittest.TestCase):
    def _core(self, engine, plan, results):
        return BrainCore(_cb(), planner=_StubPlanner(plan),
                         skill_manager=_StubManager(results),
                         reflection_engine=engine)

    def test_reflection_attached_on_success(self):
        eng = _CountingEngine()
        plan = Plan(tasks=[Task(intent="t", skill_id="s")])
        core = self._core(eng, plan, [SkillResult(skill_id="s", ok=True)])
        result = asyncio.run(core.handle(BrainRequest(text="x", request_id="r1")))
        self.assertTrue(result.handled)
        self.assertIsInstance(result.reflection, Reflection)
        self.assertEqual(result.reflection.request_id, "r1")
        self.assertTrue(result.reflection.success)

    def test_reflection_attached_on_decline(self):
        eng = _CountingEngine()
        plan = Plan(tasks=[Task(intent="t", skill_id="s")])
        core = self._core(eng, plan, [SkillResult(skill_id="s", ok=False, error="e")])
        result = asyncio.run(core.handle(BrainRequest(text="x", request_id="r2")))
        self.assertFalse(result.handled)  # semantics unchanged
        self.assertIsInstance(result.reflection, Reflection)  # still reflected
        self.assertFalse(result.reflection.success)

    def test_reflection_runs_exactly_once(self):
        eng = _CountingEngine()
        plan = Plan(tasks=[Task(intent="t", skill_id="s")])
        core = self._core(eng, plan, [SkillResult(skill_id="s", ok=True)])
        asyncio.run(core.handle(BrainRequest(text="x")))
        self.assertEqual(eng.calls, 1)

    def test_reflection_failure_does_not_fail_request(self):
        class _BadEngine:
            def reflect(self, *a): raise RuntimeError("boom")
        plan = Plan(tasks=[Task(intent="t", skill_id="s")])
        core = self._core(_BadEngine(), plan, [SkillResult(skill_id="s", ok=True)])
        result = asyncio.run(core.handle(BrainRequest(text="x")))
        self.assertTrue(result.handled)       # request still succeeds
        self.assertIsNone(result.reflection)  # failed reflection → None

    def test_no_engine_reflection_none(self):
        plan = Plan(tasks=[Task(intent="t", skill_id="s")])
        core = BrainCore(_cb(), planner=_StubPlanner(plan),
                         skill_manager=_StubManager([SkillResult(skill_id="s", ok=True)]))
        result = asyncio.run(core.handle(BrainRequest(text="x")))
        self.assertTrue(result.handled)
        self.assertIsNone(result.reflection)

    def test_pre_execution_decline_no_reflection(self):
        # No planner → declines before execution; nothing to reflect on.
        eng = _CountingEngine()
        core = BrainCore(_cb(), reflection_engine=eng)  # no planner/manager
        result = asyncio.run(core.handle(BrainRequest(text="x")))
        self.assertFalse(result.handled)
        self.assertIsNone(result.reflection)
        self.assertEqual(eng.calls, 0)


class TestBootstrapAndSemantics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container = DependencyContainer()
        Bootstrapper(container=cls.container, kasa_agent=None).bootstrap()

    def test_engine_injected_into_brain_core(self):
        core = self.container.resolve(IBrainCore)
        self.assertIsInstance(core._reflection_engine, ReflectionEngine)

    def test_existing_pass_through_unchanged(self):
        # Real bootstrap: executor unbound → declines. Behavior identical;
        # reflection None because nothing executed (pre-execution decline).
        core = self.container.resolve(IBrainCore)
        result = asyncio.run(core.handle(BrainRequest(text="open the quests panel")))
        self.assertIsInstance(result, BrainResult)
        self.assertFalse(result.handled)


class TestNoForbiddenImports(unittest.TestCase):
    def test_brain_core_imports(self):
        import ast
        src = (backend_dir / "brain" / "core" / "brain_core.py").read_text(encoding="utf-8")
        mods = set()
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.ImportFrom) and n.module: mods.add(n.module)
            elif isinstance(n, ast.Import): mods.update(a.name for a in n.names)
        # BrainCore must NOT hard-import a concrete engine/planner/skills;
        # reflection_engine arrives via injection (Any).
        for m in mods:
            self.assertNotIn("reflection", m, "BrainCore must not import reflection engine")
            self.assertNotIn("planning", m)
            self.assertNotIn("skills", m)


if __name__ == '__main__':
    unittest.main()
