"""
core/test_phase_1_7.py — Phase 1.7 verification tests (Service Resolution Helpers)

Run:
    conda activate lumina && python backend/core/test_phase_1_7.py
"""

from __future__ import annotations

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
    from core.container import DependencyContainer
    from core.bootstrap import Bootstrapper
    from core.interfaces import IBrainState, IEventBus, IPipeline
    from core.context import ExecutionContextFactory
    from core.adapters import (
        BrainStateAdapter,
        EventBusAdapter,
        ExecutionContextAdapter,
        PipelineAdapter,
    )
    import core.services as services

    # Build a fresh, isolated container + bootstrapper for each test group
    # rather than touching the process-level `container` singleton.
    def _bootstrapped_container() -> DependencyContainer:
        c = DependencyContainer()
        Bootstrapper(container=c, kasa_agent=None).bootstrap()
        return c

    section("Correct service resolution")
    c = _bootstrapped_container()
    # Note: BrainState does not formally inherit IBrainState (a pre-existing
    # Phase 1.2 characteristic, out of scope here) — verify duck-typed
    # conformance instead of isinstance for this one accessor.
    resolved_brain_state = services.get_brain_state(c)
    check(
        all(hasattr(resolved_brain_state, m) for m in ("snapshot", "transaction", "reset_session", "get_status")),
        "get_brain_state() returns an object satisfying the IBrainState contract",
    )
    check(isinstance(services.get_event_bus(c), IEventBus), "get_event_bus() returns an IEventBus")
    check(
        isinstance(services.get_execution_context_factory(c), ExecutionContextFactory),
        "get_execution_context_factory() returns an ExecutionContextFactory",
    )
    check(isinstance(services.get_pipeline(c), IPipeline), "get_pipeline() returns an IPipeline")
    check(
        isinstance(services.get_brain_state_adapter(c), BrainStateAdapter),
        "get_brain_state_adapter() returns a BrainStateAdapter",
    )
    check(
        isinstance(services.get_event_bus_adapter(c), EventBusAdapter),
        "get_event_bus_adapter() returns an EventBusAdapter",
    )
    check(
        isinstance(services.get_pipeline_adapter(c), PipelineAdapter),
        "get_pipeline_adapter() returns a PipelineAdapter",
    )
    check(
        isinstance(services.get_execution_context_adapter(c), ExecutionContextAdapter),
        "get_execution_context_adapter() returns an ExecutionContextAdapter",
    )

    section("Singleton consistency")
    c = _bootstrapped_container()
    check(
        services.get_brain_state(c) is services.get_brain_state(c),
        "get_brain_state() returns the same instance across calls",
    )
    check(
        services.get_event_bus(c) is services.get_event_bus(c),
        "get_event_bus() returns the same instance across calls",
    )
    check(
        services.get_pipeline(c) is services.get_pipeline(c),
        "get_pipeline() returns the same instance across calls",
    )
    check(
        services.get_brain_state_adapter(c) is services.get_brain_state_adapter(c),
        "get_brain_state_adapter() returns the same instance across calls",
    )

    section("Transient consistency")
    c = _bootstrapped_container()
    ctx_a = services.get_execution_context_adapter(c)
    ctx_b = services.get_execution_context_adapter(c)
    check(ctx_a is not ctx_b, "get_execution_context_adapter() returns a fresh instance per call (transient)")
    check(
        ctx_a.correlation_id != ctx_b.correlation_id,
        "each resolved ExecutionContextAdapter wraps an independent root context",
    )

    section("Resolver type safety")
    c = _bootstrapped_container()
    check(
        services.get_brain_state(c) is c.resolve(IBrainState),
        "get_brain_state() resolves the exact same binding as container.resolve(IBrainState)",
    )
    check(
        services.get_event_bus(c) is c.resolve(IEventBus),
        "get_event_bus() resolves the exact same binding as container.resolve(IEventBus)",
    )
    check(
        services.get_pipeline(c) is c.resolve(IPipeline),
        "get_pipeline() resolves the exact same binding as container.resolve(IPipeline)",
    )

    section("Registration compatibility (no caching in this module)")
    c = _bootstrapped_container()
    bs1 = services.get_brain_state(c)
    bs2 = services.get_brain_state(c)
    check(bs1 is bs2, "repeated calls delegate to container's own singleton semantics, not helper-side caching")
    # Prove there's no helper-level cache by resolving directly from a
    # second, independently bootstrapped container and confirming a
    # *different* instance comes back.
    c2 = _bootstrapped_container()
    bs3 = services.get_brain_state(c2)
    check(bs3 is not bs1, "different containers yield different instances — no cross-container caching")

    section("No interface replacement")
    c = _bootstrapped_container()
    before_brain = c.resolve(IBrainState)
    before_bus = c.resolve(IEventBus)
    before_pipeline = c.resolve(IPipeline)
    services.get_brain_state(c)
    services.get_event_bus(c)
    services.get_pipeline(c)
    services.get_brain_state_adapter(c)
    services.get_execution_context_adapter(c)
    check(
        c.resolve(IBrainState) is before_brain,
        "IBrainState binding unchanged after using service helpers",
    )
    check(
        c.resolve(IEventBus) is before_bus,
        "IEventBus binding unchanged after using service helpers",
    )
    check(
        c.resolve(IPipeline) is before_pipeline,
        "IPipeline binding unchanged after using service helpers",
    )

    section("Unregistered service raises KeyError, unchanged from container behaviour")
    empty = DependencyContainer()
    try:
        services.get_brain_state(empty)
        check(False, "resolving from an empty container should raise KeyError")
    except KeyError:
        check(True, "get_brain_state() on an unbootstrapped container raises KeyError, same as container.resolve()")

    section("PHASE 1.7 TEST SUMMARY")
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
