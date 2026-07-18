"""
tests/test_phase_5_3.py — Milestone 5.3 Verification (LLMPlanner + PlannerChain)

Verifies:
  - LLMPlanner / PlannerChain resolve from DI (singletons)
  - RuntimeFacade exposes both
  - IPlanner binding UNCHANGED (still RulePlanner — no runtime wiring)
  - Unbound LLMPlanner is inert (None, never raises)
  - Bound (fake-gateway) LLMPlanner returns valid, serializable Plans
  - Hallucinated skill ids are unbound, never invented
  - Chain: deterministic requests -> RulePlanner (gateway NOT called);
           unknown requests -> LLMPlanner
  - Planner never executes (no SkillManager/executor interaction)
  - No SDK imports inside brain/planning/llm_planner.py
  - server.py untouched by Phase 5.3
  - No circular imports; metadata registry unchanged (11)

Stdlib unittest; heavy deps mocked (established pattern).
"""

import json
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
from brain.core.interfaces import IPlanner
from brain.core.models import BrainRequest, Plan
from brain.core.context_builder import ContextBuilder
from brain.planning.rule_planner import RulePlanner
from brain.planning.llm_planner import LLMPlanner, PlannerChain
from brain.skills.registry import SkillRegistry
from brain.skills.models import SkillSpec


def _bootstrapped():
    container = DependencyContainer()
    Bootstrapper(container=container, kasa_agent=None).bootstrap()
    return container


def _ctx(text):
    return ContextBuilder(brain_state=None).build(BrainRequest(text=text))


class _FakeGateway:
    """Sync-returning IModelGateway stand-in that records calls."""
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_text(self, prompt, system_instruction="", temperature=1.0):
        self.calls.append({"prompt": prompt, "temperature": temperature})
        return self.response


def _seeded_registry():
    r = SkillRegistry()
    r.register(SkillSpec(id="legacy.browser", name="Browser", provider="legacy"))
    r.register(SkillSpec(id="legacy.memory", name="Memory", provider="legacy"))
    r.register(SkillSpec(id="legacy.cad", name="CAD", provider="legacy"))
    return r


class TestPhase5_3_DI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container = _bootstrapped()
        cls.facade = RuntimeFacade(cls.container)

    def test_llm_planner_resolves(self):
        p = self.container.resolve(LLMPlanner)
        self.assertIsInstance(p, LLMPlanner)
        self.assertIs(p, self.container.resolve(LLMPlanner))

    def test_planner_chain_resolves(self):
        c = self.container.resolve(PlannerChain)
        self.assertIsInstance(c, PlannerChain)
        self.assertIs(c, self.container.resolve(PlannerChain))

    def test_iplanner_binding_unchanged(self):
        """No runtime wiring: IPlanner must still resolve RulePlanner."""
        self.assertIsInstance(self.container.resolve(IPlanner), RulePlanner)

    def test_runtime_facade_exposes_both(self):
        self.assertIs(self.facade.llm_planner, self.container.resolve(LLMPlanner))
        self.assertIs(self.facade.planner_chain, self.container.resolve(PlannerChain))

    def test_metadata_registry_unchanged(self):
        from core.metadata import ServiceMetadataRegistry
        self.assertEqual(len(self.container.resolve(ServiceMetadataRegistry)), 11)


class TestPhase5_3_Unbound(unittest.TestCase):
    def test_unbound_planner_is_inert(self):
        planner = LLMPlanner(model_gateway=None, skill_registry=_seeded_registry())
        self.assertIsNone(planner.plan(_ctx("open my browser")))

    def test_di_registered_planner_is_unbound_and_inert(self):
        container = _bootstrapped()
        planner = container.resolve(LLMPlanner)
        self.assertIsNone(planner.plan(_ctx("write me a haiku about rain")))


class TestPhase5_3_Planning(unittest.TestCase):
    def _planner(self, response):
        gw = _FakeGateway(response)
        return LLMPlanner(model_gateway=gw, skill_registry=_seeded_registry()), gw

    def test_single_task_plan(self):
        planner, gw = self._planner(json.dumps({
            "tasks": [{"intent": "open browser", "skill_id": "legacy.browser",
                       "params": {}}],
            "confidence": 0.9, "rationale": "browser request",
        }))
        plan = planner.plan(_ctx("Open my browser"))
        self.assertIsInstance(plan, Plan)
        self.assertEqual(len(plan.tasks), 1)
        self.assertEqual(plan.tasks[0].skill_id, "legacy.browser")
        self.assertEqual(plan.confidence, 0.9)
        self.assertEqual(plan.rationale, "browser request")
        self.assertEqual(len(gw.calls), 1)
        self.assertEqual(gw.calls[0]["temperature"], 0.0)
        # Catalog present in prompt
        self.assertIn("legacy.browser", gw.calls[0]["prompt"])

    def test_multi_task_ordered_plan(self):
        planner, _ = self._planner(json.dumps({
            "tasks": [
                {"intent": "open cad", "skill_id": "legacy.cad", "params": {}},
                {"intent": "create gear", "skill_id": "legacy.cad",
                 "params": {"shape": "gear"}},
            ],
            "confidence": 0.8, "rationale": "two steps",
        }))
        plan = planner.plan(_ctx("Open CAD and create a gear"))
        self.assertEqual([t.intent for t in plan.tasks], ["open cad", "create gear"])
        self.assertEqual(plan.tasks[1].params, {"shape": "gear"})
        self.assertEqual(plan.strategy, "sequential")

    def test_plan_is_serializable_and_data_only(self):
        planner, _ = self._planner(json.dumps({
            "tasks": [{"intent": "remember", "skill_id": "legacy.memory",
                       "params": {"content": "printer is in the lab"}}],
            "confidence": 1.0, "rationale": "memory",
        }))
        plan = planner.plan(_ctx("Remember that my printer is in the lab"))
        # Round-trips through JSON => no callbacks/executables inside
        dumped = plan.model_dump_json()
        self.assertIn("printer is in the lab", dumped)
        json.loads(dumped)

    def test_hallucinated_skill_id_is_unbound(self):
        planner, _ = self._planner(json.dumps({
            "tasks": [{"intent": "launch rocket", "skill_id": "legacy.rocket",
                       "params": {}}],
            "confidence": 0.7, "rationale": "x",
        }))
        plan = planner.plan(_ctx("launch a rocket"))
        self.assertIsNotNone(plan)
        self.assertIsNone(plan.tasks[0].skill_id,
                          "Unknown skill ids must be unbound, never kept")

    def test_markdown_fenced_json_accepted(self):
        fenced = "```json\n" + json.dumps({
            "tasks": [{"intent": "search docs", "skill_id": "legacy.browser",
                       "params": {"query": "Arduino documentation"}}],
            "confidence": 0.85, "rationale": "web search",
        }) + "\n```"
        planner, _ = self._planner(fenced)
        plan = planner.plan(_ctx("Search for Arduino documentation"))
        self.assertEqual(plan.tasks[0].params["query"], "Arduino documentation")

    def test_garbage_output_returns_none(self):
        for bad in ("not json at all", "", '{"tasks": []}', '{"tasks": "x"}',
                    '[1,2,3]'):
            planner, _ = self._planner(bad)
            self.assertIsNone(planner.plan(_ctx("do something")), f"bad={bad!r}")

    def test_gateway_exception_returns_none(self):
        class _Boom:
            def generate_text(self, *a, **k):
                raise RuntimeError("model down")
        planner = LLMPlanner(model_gateway=_Boom(), skill_registry=_seeded_registry())
        self.assertIsNone(planner.plan(_ctx("do something")))

    def test_voice_tool_and_empty_not_planned(self):
        planner, gw = self._planner('{"tasks": []}')
        ctx = ContextBuilder(brain_state=None).build(
            BrainRequest(channel="voice_tool", text="x", tool_call={"name": "n"}))
        self.assertIsNone(planner.plan(ctx))
        self.assertIsNone(planner.plan(_ctx("")))
        self.assertEqual(gw.calls, [], "Gateway must not be called for these")

    def test_async_gateway_supported(self):
        class _AsyncGW:
            async def generate_text(self, prompt, system_instruction="", temperature=1.0):
                return json.dumps({
                    "tasks": [{"intent": "open browser",
                               "skill_id": "legacy.browser", "params": {}}],
                    "confidence": 0.9, "rationale": "async",
                })
        planner = LLMPlanner(model_gateway=_AsyncGW(), skill_registry=_seeded_registry())
        plan = planner.plan(_ctx("Open my browser"))
        self.assertEqual(plan.tasks[0].skill_id, "legacy.browser")


class TestPhase5_3_Chain(unittest.TestCase):
    def _chain(self, response):
        gw = _FakeGateway(response)
        llm = LLMPlanner(model_gateway=gw, skill_registry=_seeded_registry())
        return PlannerChain([RulePlanner(), llm]), gw

    def test_deterministic_request_handled_by_rule_planner(self):
        chain, gw = self._chain('{"tasks": []}')
        plan = chain.plan(_ctx("open the settings panel"))
        self.assertIsNotNone(plan)
        self.assertEqual(plan.tasks[0].skill_id, "legacy.navigate_ui")
        self.assertEqual(gw.calls, [],
                         "LLM gateway must NOT be called when RulePlanner matches")

    def test_unknown_request_falls_through_to_llm(self):
        chain, gw = self._chain(json.dumps({
            "tasks": [{"intent": "search docs", "skill_id": "legacy.browser",
                       "params": {"query": "Arduino"}}],
            "confidence": 0.8, "rationale": "fallback",
        }))
        plan = chain.plan(_ctx("Search for Arduino documentation"))
        self.assertIsNotNone(plan)
        self.assertEqual(plan.tasks[0].skill_id, "legacy.browser")
        self.assertEqual(len(gw.calls), 1)

    def test_nothing_matches_returns_none(self):
        chain, _ = self._chain("garbage")
        self.assertIsNone(chain.plan(_ctx("completely unplannable gibberish")))


class TestPhase5_3_Boundaries(unittest.TestCase):
    @staticmethod
    def _imported_modules():
        """All module names imported by llm_planner.py (AST — ignores
        docstrings/comments)."""
        import ast
        source = (backend_dir / "brain" / "planning" / "llm_planner.py").read_text(
            encoding='utf-8')
        modules = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        return modules

    def test_no_sdk_imports_in_llm_planner(self):
        modules = self._imported_modules()
        for mod in modules:
            root = mod.split(".")[0]
            self.assertNotIn(root, ("google", "openai", "anthropic", "genai"),
                             f"llm_planner.py must not import SDK module '{mod}'")

    def test_planner_never_touches_skill_manager(self):
        modules = self._imported_modules()
        self.assertNotIn("brain.skills.manager", modules)
        for mod in modules:
            self.assertNotIn("executor", mod,
                             f"llm_planner.py must not import executors ('{mod}')")

    def test_server_has_no_phase_5_3_references(self):
        source = (backend_dir / "server.py").read_text(encoding='utf-8')
        for token in ("LLMPlanner", "PlannerChain", "llm_planner"):
            self.assertNotIn(token, source)

    def test_no_circular_imports(self):
        import importlib
        import brain.planning
        importlib.reload(brain.planning)


if __name__ == '__main__':
    unittest.main()
