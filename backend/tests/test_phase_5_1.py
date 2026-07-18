"""
tests/test_phase_5_1.py — Milestone 5.1 Verification (BrainCore Skeleton)

Verifies (per Phase 5.1 spec):
  - BrainCore resolves from DI
  - RuntimeFacade exposes BrainCore (and ContextBuilder)
  - BrainCore.handle() returns a BrainResult (pass-through, handled=False)
  - ContextBuilder returns a BrainContext
  - Models are frozen value objects
  - No runtime behavior changes (BrainCore not referenced by server.py)

Stdlib unittest (pytest not provisioned in the lumina env).
Heavy optional deps are mocked before core imports, matching the pattern
established in test_phase_4_4.py / test_phase_4_5.py.
"""

import asyncio
import unittest
from unittest.mock import MagicMock
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Mock heavy dependencies before importing core modules
sys.modules.setdefault('google', MagicMock())
sys.modules.setdefault('google.genai', MagicMock())
sys.modules.setdefault('google.genai.types', MagicMock())

from core.container import DependencyContainer
from core.bootstrap import Bootstrapper
from core.runtime_facade import RuntimeFacade
from brain.core.interfaces import IBrainCore, IContextBuilder
from brain.core.models import BrainRequest, BrainContext, BrainResult, Plan, Task, Reflection
from brain.core.context_builder import ContextBuilder
from brain.core.brain_core import BrainCore


def _bootstrapped():
    """Fresh isolated container + bootstrapper (no kasa, no app host)."""
    container = DependencyContainer()
    bootstrapper = Bootstrapper(container=container, kasa_agent=None)
    bootstrapper.bootstrap()
    return container, bootstrapper


class TestPhase5_1_DI(unittest.TestCase):
    """BrainCore skeleton is DI-owned and facade-exposed."""

    @classmethod
    def setUpClass(cls):
        cls.container, cls.bootstrapper = _bootstrapped()

    def test_brain_core_resolves_from_di(self):
        core1 = self.container.resolve(IBrainCore)
        core2 = self.container.resolve(IBrainCore)
        self.assertIsInstance(core1, BrainCore)
        self.assertIs(core1, core2, "IBrainCore must be a singleton")

    def test_context_builder_resolves_from_di(self):
        cb1 = self.container.resolve(IContextBuilder)
        cb2 = self.container.resolve(IContextBuilder)
        self.assertIsInstance(cb1, ContextBuilder)
        self.assertIs(cb1, cb2, "IContextBuilder must be a singleton")

    def test_runtime_facade_exposes_brain_core(self):
        facade = RuntimeFacade(self.container)
        self.assertIs(facade.brain_core, self.container.resolve(IBrainCore))
        self.assertIs(facade.context_builder, self.container.resolve(IContextBuilder))

    def test_bootstrapper_holds_references(self):
        self.assertIsNotNone(self.bootstrapper.brain_core)
        self.assertIsNotNone(self.bootstrapper.context_builder)


class TestPhase5_1_Behavior(unittest.TestCase):
    """handle() and build() produce the correct value objects — no cognition."""

    @classmethod
    def setUpClass(cls):
        cls.container, cls.bootstrapper = _bootstrapped()
        cls.facade = RuntimeFacade(cls.container)

    def test_handle_returns_brain_result(self):
        request = BrainRequest(channel="text", text="hello lumina")
        result = asyncio.run(self.facade.brain_core.handle(request))
        self.assertIsInstance(result, BrainResult)
        self.assertEqual(result.request_id, request.request_id)
        self.assertFalse(result.handled, "Phase 5.1 pass-through must set handled=False")
        self.assertEqual(result.response_text, "")
        self.assertIsNone(result.plan)
        self.assertIsNone(result.reflection)

    def test_context_builder_returns_brain_context(self):
        request = BrainRequest(channel="rest", text="status?")
        context = self.facade.context_builder.build(request)
        self.assertIsInstance(context, BrainContext)
        self.assertIs(context.request, request)
        # BrainState is registered by Bootstrapper → snapshot extract present
        self.assertIsInstance(context.brain_snapshot, dict)
        # Enrichment fields empty in 5.1
        self.assertEqual(context.memories, [])
        self.assertEqual(context.workspace_ctx, {})
        self.assertEqual(context.persona_state, {})
        self.assertEqual(context.recent_history, [])

    def test_context_builder_without_brain_state(self):
        cb = ContextBuilder(brain_state=None)
        ctx = cb.build(BrainRequest(text="x"))
        self.assertEqual(ctx.brain_snapshot, {})

    def test_handle_does_not_mutate_state(self):
        """BrainCore.handle() must be read-only w.r.t. BrainState."""
        from core.interfaces import IBrainState
        state = self.container.resolve(IBrainState)

        def _stable(status):
            # snapshot_age_s is wall-clock derived and drifts between calls
            return {k: v for k, v in status.items() if k != "snapshot_age_s"}

        before = _stable(state.get_status())
        asyncio.run(self.facade.brain_core.handle(BrainRequest(text="noop")))
        after = _stable(state.get_status())
        self.assertEqual(before, after, "handle() must not mutate BrainState")


class TestPhase5_1_Models(unittest.TestCase):
    """Value objects are frozen and default-complete."""

    def test_models_are_frozen(self):
        req = BrainRequest(text="a")
        with self.assertRaises(Exception):
            req.text = "b"
        res = BrainResult(request_id="r1")
        with self.assertRaises(Exception):
            res.response_text = "changed"

    def test_plan_and_task_defaults(self):
        t = Task(intent="do a thing")
        p = Plan(tasks=[t])
        self.assertIsNone(t.skill_id)
        self.assertFalse(t.needs_confirmation)
        self.assertEqual(p.strategy, "sequential")
        self.assertEqual(len(p.tasks), 1)

    def test_reflection_defaults(self):
        r = Reflection(request_id="r1")
        self.assertTrue(r.success)
        self.assertEqual(r.skills_used, [])
        self.assertEqual(r.confidence, 1.0)

    def test_unique_ids(self):
        self.assertNotEqual(BrainRequest().request_id, BrainRequest().request_id)
        self.assertNotEqual(Task(intent="x").id, Task(intent="x").id)


class TestPhase5_1_No_Runtime_Wiring(unittest.TestCase):
    """Guard: Phase 5.1 must not change runtime behavior."""

    def test_server_brain_core_wiring_is_flag_gated(self):
        """Phase 5.4 Order 8 wired the Brain path into server.py behind the
        brain_core_enabled flag (default False). The invariant is no longer
        'server has no brain reference' but 'any brain reference is flag-gated
        and defaults off'."""
        server_path = backend_dir / "server.py"
        source = server_path.read_text(encoding='utf-8')
        # Flag exists and defaults off.
        self.assertIn('"brain_core_enabled": False', source)
        # The intercept is gated by that flag.
        self.assertIn('SETTINGS.get("brain_core_enabled", False)', source)

    def test_no_circular_imports(self):
        """brain.core package imports cleanly in one pass."""
        import importlib
        import brain.core
        importlib.reload(brain.core)  # would raise on circular import


if __name__ == '__main__':
    unittest.main()
