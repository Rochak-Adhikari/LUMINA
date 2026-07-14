"""
core/test_phase_1_6.py — Phase 1.6 verification tests (Infrastructure Adapters)

Run:
    conda activate lumina && python backend/core/test_phase_1_6.py
"""

from __future__ import annotations

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_passed = 0
_failed = 0


def check(condition: bool, description: str) -> None:
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  [PASS] {description}")
    else:
        _failed += 1
        print(f"  [FAIL] {description}")


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def run() -> None:
    from core.adapters import (
        BrainStateAdapter,
        EventBusAdapter,
        ExecutionContextAdapter,
        PipelineAdapter,
    )
    from core.interfaces import IBrainState, IEventBus, IExecutionContext, IPipeline
    from core.container import DependencyContainer
    from brain.state import BrainState
    from brain.events import InProcessEventBus
    from core.context import ExecutionContext, ExecutionContextFactory
    from core.pipeline import PipelineBuilder

    section("BrainStateAdapter — forwarding")
    real_brain = BrainState()
    adapter = BrainStateAdapter(real_brain)
    check(isinstance(adapter, IBrainState), "BrainStateAdapter implements IBrainState")
    check(adapter.snapshot() == real_brain.snapshot(), "snapshot() forwards identical value")
    with adapter.transaction() as draft:
        draft.current_project = "phase16-test"
    check(
        real_brain.snapshot().workspace.current_project == "phase16-test",
        "transaction() forwarded write is visible on the wrapped BrainState",
    )
    check(adapter.get_status() == real_brain.get_status(), "get_status() forwards identical value")
    adapter.reset_session()
    check(real_brain.snapshot().session.session_id is None, "reset_session() forwarded to wrapped BrainState")

    section("BrainStateAdapter — exception propagation")
    class _ExplodingBrainState(IBrainState):
        def snapshot(self):
            raise ValueError("boom")
        def transaction(self):
            raise ValueError("boom")
        def reset_session(self):
            raise ValueError("boom")
        def get_status(self):
            raise ValueError("boom")

    exploding_adapter = BrainStateAdapter(_ExplodingBrainState())
    try:
        exploding_adapter.snapshot()
        check(False, "exception from wrapped service should propagate unchanged")
    except ValueError as e:
        check(str(e) == "boom", "ValueError propagates through adapter unchanged")

    section("EventBusAdapter — forwarding")
    real_bus = InProcessEventBus()
    bus_adapter = EventBusAdapter(real_bus)
    check(isinstance(bus_adapter, IEventBus), "EventBusAdapter implements IEventBus")

    received = []

    async def _handler(topic, payload):
        received.append((topic, payload))

    async def _bus_flow():
        token = await bus_adapter.subscribe("test.*", _handler)
        await bus_adapter.publish("test.event", {"x": 1})
        await bus_adapter.unsubscribe(token)
        await bus_adapter.publish("test.event", {"x": 2})

    asyncio.run(_bus_flow())
    check(received == [("test.event", {"x": 1})], "publish/subscribe/unsubscribe forward with correct ordering")

    section("ExecutionContextAdapter — forwarding & child derivation")
    root = ExecutionContext(session_id="s1")
    ctx_adapter = ExecutionContextAdapter(root)
    check(isinstance(ctx_adapter, IExecutionContext), "ExecutionContextAdapter implements IExecutionContext")
    check(ctx_adapter.context_id == root.context_id, "attribute access forwards to wrapped context (__getattr__)")

    child_adapter = ctx_adapter.child(workspace_id="alpha")
    check(isinstance(child_adapter, ExecutionContextAdapter), "child() returns another ExecutionContextAdapter")
    check(child_adapter.correlation_id == root.correlation_id, "child adapter preserves correlation_id")
    check(child_adapter.parent_id == root.context_id, "child adapter's parent_id is the root's context_id")
    check(child_adapter.workspace_id == "alpha", "child adapter reflects override")

    section("PipelineAdapter — forwarding")
    calls = []

    class _RecordingMiddleware:
        async def handle(self, context, call_next):
            calls.append("mw")
            return await call_next(context)

    real_pipeline = PipelineBuilder().build()
    pipe_adapter = PipelineAdapter(real_pipeline)
    check(isinstance(pipe_adapter, IPipeline), "PipelineAdapter implements IPipeline")
    try:
        pipe_adapter.register(_RecordingMiddleware())
        check(False, "register() on a sealed pipeline should raise via adapter")
    except RuntimeError:
        check(True, "RuntimeError from sealed pipeline propagates through adapter unchanged")

    unsealed = PipelineBuilder()._pipeline  # test-only: pre-seal access to verify pass-through
    unsealed_adapter = PipelineAdapter(unsealed)
    unsealed_adapter.register(_RecordingMiddleware())
    check(unsealed.middleware_count == 1, "register() via adapter forwards to wrapped pipeline")

    from core.pipeline import PipelineContext
    result = asyncio.run(unsealed_adapter.execute(PipelineContext(execution_context=root)))
    check(calls == ["mw"], "execute() via adapter runs wrapped pipeline's middleware")
    unsealed_adapter.clear()
    check(unsealed.middleware_count == 0, "clear() via adapter forwards to wrapped pipeline")

    section("DI Container integration")
    c = DependencyContainer()
    c.register_instance(BrainStateAdapter, adapter)
    c.register_instance(EventBusAdapter, bus_adapter)
    c.register_instance(PipelineAdapter, pipe_adapter)
    factory = ExecutionContextFactory()
    c.register_transient(ExecutionContextAdapter, lambda: ExecutionContextAdapter(factory.create()))
    check(c.resolve(BrainStateAdapter) is adapter, "BrainStateAdapter resolves from container")
    check(c.resolve(EventBusAdapter) is bus_adapter, "EventBusAdapter resolves from container")
    check(c.resolve(PipelineAdapter) is pipe_adapter, "PipelineAdapter resolves from container")
    first = c.resolve(ExecutionContextAdapter)
    second = c.resolve(ExecutionContextAdapter)
    check(first is not second, "ExecutionContextAdapter is transient — new instance per resolve()")

    section("Bootstrapper integration — coexistence")
    from core.bootstrap import Bootstrapper
    bc = DependencyContainer()
    bs = Bootstrapper(container=bc, kasa_agent=None)
    bs.bootstrap()
    check(bs.brain_state_adapter is not None, "Bootstrapper constructs BrainStateAdapter")
    check(bs.event_bus_adapter is not None, "Bootstrapper constructs EventBusAdapter")
    check(bs.pipeline_adapter is not None, "Bootstrapper constructs PipelineAdapter")
    check(
        bc.resolve(IBrainState) is bs.brain_state,
        "Legacy IBrainState registration is untouched — resolves to the concrete BrainState, not the adapter",
    )
    check(
        bc.resolve(BrainStateAdapter)._brain_state is bs.brain_state,
        "BrainStateAdapter wraps the same BrainState instance registered under IBrainState",
    )
    check(
        bc.resolve(IEventBus) is bs.event_bus,
        "Legacy IEventBus registration is untouched — resolves to the concrete InProcessEventBus",
    )
    check(
        bc.resolve(IPipeline) is bs.pipeline,
        "Legacy IPipeline registration is untouched — resolves to the concrete RequestPipeline",
    )
    ctx_from_container = bc.resolve(ExecutionContextAdapter)
    check(isinstance(ctx_from_container, ExecutionContextAdapter), "ExecutionContextAdapter resolves from Bootstrapper-built container")

    section("PHASE 1.6 TEST SUMMARY")
    print(f"  Passed: {_passed}")
    print(f"  Failed: {_failed}")
    print("=" * 60)
    if _failed == 0:
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    run()
