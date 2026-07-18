"""
tests/test_phase_5_4.py — Phase 5.4 verification (grows step by step)

Step 0 (this revision): skill catalog truth-alignment.
  - Every BUILTIN_SKILLS provider_ref is a REAL key in the union of the two
    live legacy registries (ToolDispatcherRegistry ∪ ACTION_REGISTRY).
  - Skill ids unique; provider is 'legacy' for all builtins.
  - Bootstrap seeds the rewritten catalog; DI unchanged otherwise.
  - No runtime behavior change (BrainCore still pass-through; server.py
    still has zero Phase 5 references).

Stdlib unittest; heavy deps mocked (established pattern).
"""

import asyncio
import unittest
from unittest.mock import MagicMock
from pathlib import Path
from types import SimpleNamespace
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

sys.modules.setdefault('google', MagicMock())
sys.modules.setdefault('google.genai', MagicMock())
sys.modules.setdefault('google.genai.types', MagicMock())

from core.container import DependencyContainer
from core.bootstrap import Bootstrapper
from brain.core.interfaces import IBrainCore
from brain.core.models import BrainRequest, BrainResult
from brain.skills.registry import SkillRegistry
from brain.skills.builtin import BUILTIN_SKILLS, _TIER1_SKILLS, _TIER2_SKILLS


def _live_registry_keys():
    """Union of both live legacy dispatch registries."""
    from core.registry import ToolDispatcherRegistry
    import core.tool_handlers  # noqa: F401 — populates the registry
    from actions import ACTION_REGISTRY
    tier1 = set(ToolDispatcherRegistry.keys())
    tier2 = set(ACTION_REGISTRY.keys())
    return tier1, tier2


class TestStep0_CatalogTruthAlignment(unittest.TestCase):
    """Every provider_ref must name a real, dispatchable legacy tool."""

    @classmethod
    def setUpClass(cls):
        cls.tier1, cls.tier2 = _live_registry_keys()
        cls.union = cls.tier1 | cls.tier2

    def test_every_provider_ref_is_real(self):
        for spec in BUILTIN_SKILLS:
            self.assertIn(
                spec.provider_ref, self.union,
                f"SkillSpec '{spec.id}' has provider_ref "
                f"'{spec.provider_ref}' which matches NO key in "
                f"ToolDispatcherRegistry or ACTION_REGISTRY",
            )

    def test_tier1_specs_point_at_tool_dispatcher(self):
        for spec in _TIER1_SKILLS:
            self.assertIn(spec.provider_ref, self.tier1,
                          f"'{spec.id}' should be a tier-1 tool")

    def test_tier2_specs_point_at_action_registry(self):
        for spec in _TIER2_SKILLS:
            self.assertIn(spec.provider_ref, self.tier2,
                          f"'{spec.id}' should be a tier-2 action")

    def test_full_tier1_coverage(self):
        """Every ToolDispatcherRegistry tool has a SkillSpec (16/16)."""
        covered = {s.provider_ref for s in _TIER1_SKILLS}
        self.assertEqual(covered, self.tier1,
                         f"Uncovered tier-1 tools: {self.tier1 - covered}")

    def test_ids_unique_and_legacy_provider(self):
        ids = [s.id for s in BUILTIN_SKILLS]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate skill ids")
        for spec in BUILTIN_SKILLS:
            self.assertEqual(spec.provider, "legacy")
            self.assertTrue(spec.id.startswith("legacy."))

    def test_no_memory_skill(self):
        """Blueprint D1: no memory tool exists in either registry, so no
        memory SkillSpec may exist until a real target does."""
        for spec in BUILTIN_SKILLS:
            self.assertNotIn("memory", spec.id)


class TestStep0_BootstrapSeeding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container = DependencyContainer()
        Bootstrapper(container=cls.container, kasa_agent=None).bootstrap()

    def test_registry_seeded_with_rewritten_catalog(self):
        registry = self.container.resolve(SkillRegistry)
        self.assertEqual(len(registry), len(BUILTIN_SKILLS))
        self.assertIsNotNone(registry.get("legacy.navigate_ui"))
        self.assertIsNone(registry.get("legacy.navigation"),
                          "Old fictional id must be gone")
        self.assertIsNone(registry.get("legacy.memory"),
                          "Old fictional id must be gone")

    def test_runtime_still_unchanged(self):
        """BrainCore remains pass-through; no server wiring in Step 0."""
        core = self.container.resolve(IBrainCore)
        result = asyncio.run(core.handle(BrainRequest(text="open the quests panel")))
        self.assertIsInstance(result, BrainResult)
        self.assertFalse(result.handled)
        source = (backend_dir / "server.py").read_text(encoding='utf-8')
        for token in ("BrainCore", "brain.skills", "brain.planning",
                      "brain_core_enabled"):
            self.assertNotIn(token, source,
                             f"server.py must not reference {token} in Step 0")


class TestStep1_RulePlannerContract(unittest.TestCase):
    """Step 1: RulePlanner output must reference the truth-aligned catalog.

    Every skill_id a RulePlanner Plan emits must exist in BUILTIN_SKILLS,
    and navigation params must carry a real panel. This is the D6-analog of
    Step 0's provider_ref pinning test — it prevents contract drift.
    """

    @classmethod
    def setUpClass(cls):
        from brain.planning.rule_planner import RulePlanner
        cls.planner = RulePlanner()
        cls.catalog_ids = {s.id for s in BUILTIN_SKILLS}
        cls.panels = {"quests", "archive", "events", "settings", "home"}

    def _ctx(self, text):
        from brain.core.context_builder import ContextBuilder
        return ContextBuilder(brain_state=None).build(BrainRequest(text=text))

    def test_nav_skill_id_in_catalog(self):
        phrases = [
            "open the quests panel", "go to settings", "show my notes",
            "switch to events", "go to home", "open the calendar",
        ]
        for p in phrases:
            plan = self.planner.plan(self._ctx(p))
            self.assertIsNotNone(plan, f"expected a plan for {p!r}")
            for task in plan.tasks:
                self.assertIn(task.skill_id, self.catalog_ids,
                              f"{p!r} → skill_id {task.skill_id} not in catalog")
                self.assertIn(task.params.get("panel"), self.panels,
                              f"{p!r} → panel {task.params.get('panel')} invalid")

    def test_nav_emits_navigate_ui(self):
        plan = self.planner.plan(self._ctx("open the quests panel"))
        self.assertEqual(plan.tasks[0].skill_id, "legacy.navigate_ui")
        self.assertEqual(plan.tasks[0].params, {"panel": "quests", "view": "all"})

    def test_view_filter_detected(self):
        plan = self.planner.plan(self._ctx("show completed quests"))
        self.assertIsNotNone(plan)
        self.assertEqual(plan.tasks[0].params.get("view"), "completed")

    def test_alias_mapping(self):
        self.assertEqual(
            self.planner.plan(self._ctx("open notes")).tasks[0].params["panel"],
            "archive")
        self.assertEqual(
            self.planner.plan(self._ctx("go to the dashboard")).tasks[0].params["panel"],
            "home")

    def test_unknown_panel_abstains(self):
        self.assertIsNone(self.planner.plan(self._ctx("open the fridge")))

    def test_memory_verbs_not_planned(self):
        self.assertIsNone(self.planner.plan(self._ctx("remember that I like tea")))
        self.assertIsNone(self.planner.plan(self._ctx("forget my address")))

    def test_no_retired_ids_ever_emitted(self):
        for p in ("open quests", "remember X", "go to settings", "forget Y"):
            plan = self.planner.plan(self._ctx(p))
            if plan is not None:
                for task in plan.tasks:
                    self.assertNotIn(task.skill_id, ("legacy.navigation", "legacy.memory"),
                                     "retired skill id must never be emitted")


class TestStep2_LLMPlannerAsync(unittest.TestCase):
    """Step 2: LLMPlanner async planning path (fixes D4/D1).

    plan_async() must drive an async gateway from within a running event
    loop without a nested asyncio.run, preserve never-raise, and keep the
    synchronous plan() API backward-compatible.
    """

    @classmethod
    def setUpClass(cls):
        from brain.core.context_builder import ContextBuilder
        from brain.skills.registry import SkillRegistry as _SR
        from brain.skills.models import SkillSpec as _SS
        cls._ContextBuilder = ContextBuilder
        reg = _SR()
        reg.register(_SS(id="legacy.navigate_ui", name="Nav", provider="legacy"))
        reg.register(_SS(id="legacy.web_search", name="Web", provider="legacy"))
        cls.registry = reg

    def _ctx(self, text, channel="text", tool_call=None):
        return self._ContextBuilder(brain_state=None).build(
            BrainRequest(text=text, channel=channel, tool_call=tool_call))

    def _planner(self, response, async_gw=False):
        from brain.planning.llm_planner import LLMPlanner
        import json as _json

        class _SyncGW:
            def __init__(self, resp): self.resp = resp; self.calls = []
            def generate_text(self, prompt, system_instruction="", temperature=1.0):
                self.calls.append(prompt); return self.resp

        class _AsyncGW:
            def __init__(self, resp): self.resp = resp; self.calls = []
            async def generate_text(self, prompt, system_instruction="", temperature=1.0):
                self.calls.append(prompt); return self.resp

        gw = (_AsyncGW if async_gw else _SyncGW)(response)
        return LLMPlanner(model_gateway=gw, skill_registry=self.registry), gw

    @staticmethod
    def _plan_json(skill_id="legacy.web_search"):
        import json as _json
        return _json.dumps({
            "tasks": [{"intent": "do", "skill_id": skill_id, "params": {}}],
            "confidence": 0.8, "rationale": "x",
        })

    def test_plan_async_with_async_gateway_in_running_loop(self):
        # D4 regression: must NOT raise "asyncio.run() cannot be called from
        # a running event loop". asyncio.run drives our plan_async coroutine,
        # which internally awaits the async gateway (no nested asyncio.run).
        planner, gw = self._planner(self._plan_json(), async_gw=True)
        plan = asyncio.run(planner.plan_async(self._ctx("search the web")))
        self.assertIsNotNone(plan)
        self.assertEqual(plan.tasks[0].skill_id, "legacy.web_search")
        self.assertEqual(len(gw.calls), 1)

    def test_plan_async_with_sync_gateway(self):
        planner, _ = self._planner(self._plan_json(), async_gw=False)
        plan = asyncio.run(planner.plan_async(self._ctx("search the web")))
        self.assertIsNotNone(plan)

    def test_plan_async_no_gateway_returns_none(self):
        from brain.planning.llm_planner import LLMPlanner
        planner = LLMPlanner(model_gateway=None, skill_registry=self.registry)
        self.assertIsNone(asyncio.run(planner.plan_async(self._ctx("x"))))

    def test_plan_async_never_raises(self):
        from brain.planning.llm_planner import LLMPlanner

        class _Boom:
            async def generate_text(self, *a, **k):
                raise RuntimeError("model down")
        planner = LLMPlanner(model_gateway=_Boom(), skill_registry=self.registry)
        self.assertIsNone(asyncio.run(planner.plan_async(self._ctx("x"))))

    def test_plan_async_voice_tool_and_empty(self):
        planner, gw = self._planner(self._plan_json(), async_gw=True)
        self.assertIsNone(asyncio.run(planner.plan_async(
            self._ctx("x", channel="voice_tool", tool_call={"name": "n"}))))
        self.assertIsNone(asyncio.run(planner.plan_async(self._ctx(""))))
        self.assertEqual(gw.calls, [], "gateway must not be called for these")

    def test_chain_plan_async_rule_first(self):
        from brain.planning.llm_planner import LLMPlanner, PlannerChain
        from brain.planning.rule_planner import RulePlanner
        llm, gw = self._planner(self._plan_json(), async_gw=True)
        chain = PlannerChain([RulePlanner(), llm])
        plan = asyncio.run(chain.plan_async(self._ctx("open the quests panel")))
        self.assertIsNotNone(plan)
        self.assertEqual(plan.tasks[0].skill_id, "legacy.navigate_ui")
        self.assertEqual(gw.calls, [], "LLM gateway must NOT be called when RulePlanner matches")

    def test_chain_plan_async_llm_fallback(self):
        from brain.planning.llm_planner import LLMPlanner, PlannerChain
        from brain.planning.rule_planner import RulePlanner
        llm, gw = self._planner(self._plan_json(), async_gw=True)
        chain = PlannerChain([RulePlanner(), llm])
        plan = asyncio.run(chain.plan_async(self._ctx("search the web for arduino")))
        self.assertIsNotNone(plan)
        self.assertEqual(plan.tasks[0].skill_id, "legacy.web_search")
        self.assertEqual(len(gw.calls), 1)

    def test_sync_plan_backward_compatible(self):
        # No running loop → sync plan() with a sync gateway still works.
        planner, _ = self._planner(self._plan_json(), async_gw=False)
        plan = planner.plan(self._ctx("search the web"))
        self.assertIsNotNone(plan)

    def test_sync_plan_async_gateway_in_running_loop_returns_none(self):
        # D4 guard: sync plan() cannot drive an async gateway inside a running
        # loop; must return None (never raise), not crash.
        planner, _ = self._planner(self._plan_json(), async_gw=True)

        async def _run():
            return planner.plan(self._ctx("search the web"))
        self.assertIsNone(asyncio.run(_run()))


class TestOrder1_Hotfix(unittest.TestCase):
    """Roadmap Order 1: B1 (dispatch gate hole) + B2 (stop_audio disarm).

    These fixes live in the legacy voice loop (lumina.py) and the stop_audio
    handler (server.py) — regions that require a live Gemini session to
    exercise dynamically. Verified structurally against source, matching the
    existing server.py source-assertion pattern in this suite.
    """

    def _lumina_src(self):
        return (backend_dir / "lumina.py").read_text(encoding='utf-8')

    def _server_src(self):
        return (backend_dir / "server.py").read_text(encoding='utf-8')

    # ---- B1: dispatch runs for every registered tool -------------------

    def test_b1_dispatch_has_unknown_tool_branch(self):
        src = self._lumina_src()
        self.assertIn("no handler available", src,
                      "B1: unknown tool must get an explicit FunctionResponse")

    def test_b1_navigate_ui_not_required_in_gate_sets(self):
        # navigate_ui is a tier-1 tool; the fix means it need not appear in
        # the permission-gate sets to be dispatched. Guard against a
        # regression that re-nests dispatch under the gate by requiring the
        # B1 marker comment to be present.
        src = self._lumina_src()
        self.assertIn("B1 fix", src,
                      "B1 dispatch-dedent marker must be present")

    def test_b1_dispatch_tiers_preserved(self):
        src = self._lumina_src()
        # Two-tier order + calling conventions intact.
        self.assertIn("ToolDispatcherRegistry.contains(fc.name)", src)
        self.assertIn("elif fc.name in ACTION_REGISTRY", src)
        self.assertIn("asyncio.to_thread", src)

    # ---- B2: stop_audio must not disarm ApplicationHost ----------------

    def test_b2_stop_audio_uses_unified_shutdown_not_host_stop(self):
        src = self._server_src()
        # Locate the stop_audio function body.
        idx = src.index("async def stop_audio(")
        body = src[idx: idx + 800]
        self.assertIn('_unified_shutdown("stop_audio")', body,
                      "B2: stop_audio must call session-scoped _unified_shutdown")
        self.assertNotIn("_app_host.stop()", body,
                         "B2: stop_audio must NOT call ApplicationHost.stop()")

    def test_b2_real_shutdown_paths_still_use_host_stop(self):
        src = self._server_src()
        # The frontend shutdown socket + hook registration still route through
        # ApplicationHost (process-exit path) — unchanged by B2.
        self.assertIn("_app_host.stop()", src,
                      "process-exit shutdown must still use ApplicationHost.stop()")
        self.assertIn("register_cleanup_hook", src)


class TestOrder6_DispatchClosure(unittest.TestCase):
    """Order 6 (Step 3): session dispatch closure + executor bind/unbind.

    Dormant: nothing calls the closure at runtime yet (that is Step 6). These
    tests exercise the closure and executor binding in isolation with a fake
    AudioLoop, verifying two-tier dispatch, permission parity, the D7 liveness
    guard, and the confirmation-refusal invariant.
    """

    def setUp(self):
        from core.registry import ToolDispatcherRegistry
        from actions import ACTION_REGISTRY
        self.TDR = ToolDispatcherRegistry
        self.ACTION_REGISTRY = ACTION_REGISTRY

    def _loop(self, permissions=None, session="live", browser_mode="strict"):
        return SimpleNamespace(
            session=session,
            permissions=permissions if permissions is not None else {},
            memory_store=SimpleNamespace(name="mem"),
            _browser_confirmation_mode=browser_mode,
        )

    # ---- executor bind/unbind -----------------------------------------

    def test_executor_bind_unbind(self):
        from brain.skills.executors.legacy_tool_executor import LegacyToolExecutor
        from brain.skills.models import SkillSpec, SkillResult
        ex = LegacyToolExecutor()
        self.assertFalse(ex.is_bound)
        # unbound → inert failed result
        spec = SkillSpec(id="legacy.x", name="X", provider="legacy", provider_ref="x")
        r = asyncio.run(ex.run(spec, {}))
        self.assertFalse(r.ok)
        self.assertIn("no dispatch bound", r.error)
        # bind
        async def d(ref, params): return {"ref": ref}
        ex.bind(d)
        self.assertTrue(ex.is_bound)
        r2 = asyncio.run(ex.run(spec, {}))
        self.assertTrue(r2.ok)
        self.assertEqual(r2.output, {"ref": "x"})
        # unbind → inert again (idempotent)
        ex.unbind(); ex.unbind()
        self.assertFalse(ex.is_bound)
        self.assertFalse(asyncio.run(ex.run(spec, {})).ok)

    # ---- closure: two-tier dispatch -----------------------------------

    def test_closure_tier1_dispatch(self):
        from core.legacy_dispatch import build_session_dispatch
        loop = self._loop(permissions={"navigate_ui": True})
        dispatch = build_session_dispatch(loop)
        # navigate_ui is a real tier-1 tool; its handler calls
        # loop.on_voice_command — provide it.
        loop.on_voice_command = lambda panel, view: None
        out = asyncio.run(dispatch("navigate_ui", {"panel": "quests"}))
        self.assertIn("result", out)

    def test_closure_tier2_dispatch(self):
        from core.legacy_dispatch import build_session_dispatch
        # Register a temporary mock tier-2 action so we verify routing WITHOUT
        # invoking a real action (real actions have OS/network side effects).
        marker = "_test_order6_action"
        calls = []
        def _mock_action(params, response, player, memory):
            calls.append((dict(params), memory)); return "mock-ok"
        self.ACTION_REGISTRY[marker] = _mock_action
        try:
            loop = self._loop(permissions={marker: True})
            dispatch = build_session_dispatch(loop)
            out = asyncio.run(dispatch(marker, {"query": "x"}))
            self.assertEqual(out, "mock-ok")
            self.assertEqual(calls[0][0], {"query": "x"})
            self.assertIs(calls[0][1], loop.memory_store)
        finally:
            self.ACTION_REGISTRY.pop(marker, None)

    def test_closure_unknown_tool_raises_keyerror(self):
        from core.legacy_dispatch import build_session_dispatch
        loop = self._loop(permissions={"ghost_tool": True})
        dispatch = build_session_dispatch(loop)
        with self.assertRaises(KeyError):
            asyncio.run(dispatch("ghost_tool", {}))

    # ---- closure: permission parity -----------------------------------

    def test_closure_permission_denied(self):
        from core.legacy_dispatch import build_session_dispatch, ToolDenied
        loop = self._loop(permissions={"navigate_ui": False})
        dispatch = build_session_dispatch(loop)
        with self.assertRaises(ToolDenied):
            asyncio.run(dispatch("navigate_ui", {}))

    def test_closure_needs_confirmation_refused(self):
        from core.legacy_dispatch import build_session_dispatch, ToolNeedsConfirmation
        # Absent permission → would need confirmation → Brain path refuses.
        loop = self._loop(permissions={})
        dispatch = build_session_dispatch(loop)
        with self.assertRaises(ToolNeedsConfirmation):
            asyncio.run(dispatch("navigate_ui", {}))

    def test_closure_browser_auto_confirm_non_strict(self):
        from core.legacy_dispatch import build_session_dispatch, ToolNeedsConfirmation
        # Browser tool, non-strict mode, no explicit permission → must
        # auto-confirm (permission gate passes, no ToolNeedsConfirmation).
        # Register a mock tier-1 handler under a browser name to avoid
        # launching a real browser.
        marker = "browser_control"
        already = self.TDR.contains(marker)
        if not already:
            async def _mock_browser(fc, loop): return {"result": "mock"}
            self.TDR.register_value(marker, _mock_browser)
        try:
            loop = self._loop(permissions={}, browser_mode="auto")
            dispatch = build_session_dispatch(loop)
            out = asyncio.run(dispatch(marker, {"intent": "open_url"}))
            self.assertIsNotNone(out)  # gate passed, dispatched
        except ToolNeedsConfirmation:
            self.fail("browser tool in non-strict mode must auto-confirm")
        finally:
            if not already:
                # Remove the temporary registration.
                self.TDR._entries().pop(marker, None)

    # ---- closure: D7 liveness guard -----------------------------------

    def test_closure_stale_session_refused(self):
        from core.legacy_dispatch import build_session_dispatch, SessionGone
        loop = self._loop(permissions={"navigate_ui": True}, session="live")
        dispatch = build_session_dispatch(loop)
        # Session swapped/gone after bind → refuse.
        loop.session = None
        with self.assertRaises(SessionGone):
            asyncio.run(dispatch("navigate_ui", {}))

    def test_closure_session_replaced_refused(self):
        from core.legacy_dispatch import build_session_dispatch, SessionGone
        loop = self._loop(permissions={"navigate_ui": True}, session="s1")
        dispatch = build_session_dispatch(loop)
        loop.session = "s2"  # reconnect → different session object
        with self.assertRaises(SessionGone):
            asyncio.run(dispatch("navigate_ui", {}))

    # ---- brain import-whitelist intact --------------------------------

    def test_legacy_dispatch_lives_in_core_not_brain(self):
        # The bridge that imports legacy registries must be in core/, not
        # brain/ (brain import-whitelist).
        self.assertTrue((backend_dir / "core" / "legacy_dispatch.py").exists())
        exec_src = (backend_dir / "brain" / "skills" / "executors"
                    / "legacy_tool_executor.py").read_text(encoding='utf-8')
        for forbidden in ("ToolDispatcherRegistry", "ACTION_REGISTRY",
                          "core.registry", "from actions"):
            self.assertNotIn(forbidden, exec_src,
                             "executor must not import legacy registries")


class TestOrder7_BrainCoreOrchestration(unittest.TestCase):
    """Order 7 (Steps 4-5): BrainCore plan->execute + Bootstrapper injection
    + facade legacy_executor accessor.

    DORMANT-SAFE: with the executor unbound (default), a plannable request
    still returns handled=False (execution fails), so the existing pass-
    through contract is preserved. handled=True only when a bound executor
    succeeds — exercised here with a fake bound dispatch.
    """

    @classmethod
    def setUpClass(cls):
        cls.container = DependencyContainer()
        Bootstrapper(container=cls.container, kasa_agent=None).bootstrap()
        from core.runtime_facade import RuntimeFacade
        cls.facade = RuntimeFacade(cls.container)

    def test_brain_core_has_planner_and_manager_injected(self):
        core = self.container.resolve(IBrainCore)
        self.assertIsNotNone(core._planner)
        self.assertIsNotNone(core._skill_manager)

    def test_facade_exposes_legacy_executor(self):
        from brain.skills.executors.legacy_tool_executor import LegacyToolExecutor
        self.assertIs(self.facade.legacy_executor,
                      self.container.resolve(LegacyToolExecutor))
        self.assertFalse(self.facade.legacy_executor.is_bound)

    def test_metadata_registry_still_11(self):
        from core.metadata import ServiceMetadataRegistry
        self.assertEqual(len(self.container.resolve(ServiceMetadataRegistry)), 11)

    def test_skill_registry_still_19(self):
        self.assertEqual(len(self.container.resolve(SkillRegistry)), 19)

    def test_plannable_request_declines_when_executor_unbound(self):
        core = self.container.resolve(IBrainCore)
        result = asyncio.run(core.handle(BrainRequest(text="open the quests panel")))
        self.assertIsInstance(result, BrainResult)
        self.assertFalse(result.handled)
        self.assertIsNone(result.plan)

    def test_unrecognized_request_declines(self):
        core = self.container.resolve(IBrainCore)
        result = asyncio.run(core.handle(BrainRequest(text="write me a haiku")))
        self.assertFalse(result.handled)
        self.assertIsNone(result.plan)

    def test_bound_executor_success_yields_handled_true(self):
        from brain.skills.executors.legacy_tool_executor import LegacyToolExecutor
        executor = self.container.resolve(LegacyToolExecutor)
        core = self.container.resolve(IBrainCore)

        async def _fake_dispatch(ref, params):
            return {"ref": ref, "params": params}
        executor.bind(_fake_dispatch)
        try:
            result = asyncio.run(core.handle(BrainRequest(text="open the quests panel")))
            self.assertTrue(result.handled)
            self.assertIsNotNone(result.plan)
            self.assertEqual(result.plan.tasks[0].skill_id, "legacy.navigate_ui")
            self.assertIn("results", result.artifacts)
        finally:
            executor.unbind()
        result2 = asyncio.run(core.handle(BrainRequest(text="open the quests panel")))
        self.assertFalse(result2.handled)

    def test_bound_executor_failure_declines(self):
        from brain.skills.executors.legacy_tool_executor import LegacyToolExecutor
        executor = self.container.resolve(LegacyToolExecutor)
        core = self.container.resolve(IBrainCore)

        async def _boom(ref, params):
            raise RuntimeError("nope")
        executor.bind(_boom)
        try:
            result = asyncio.run(core.handle(BrainRequest(text="open the quests panel")))
            self.assertFalse(result.handled)
            self.assertIsNone(result.plan)
        finally:
            executor.unbind()

    def test_handle_does_not_mutate_brain_state(self):
        from core.interfaces import IBrainState
        state = self.container.resolve(IBrainState)

        def _stable(s):
            return {k: v for k, v in s.items() if k != "snapshot_age_s"}
        before = _stable(state.get_status())
        asyncio.run(self.container.resolve(IBrainCore).handle(
            BrainRequest(text="open the quests panel")))
        after = _stable(state.get_status())
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
